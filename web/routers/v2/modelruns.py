import io
import itertools
import zipfile
from pathlib import Path
from uuid import UUID

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse
from hermes_model import ModelInput
from jinja2 import Template
from sqlalchemy import text

from hermes.schemas.base import EInput, EResultType
from web import crud
from web.database import DBSessionDep
from web.routers.v2.queries.modelruns import EVENTCOUNTS
from web.schemas import (ForecastSchema, ForecastSeriesSchema,
                         ModelRunCatalogSchema, ModelRunRateGridSchema)

router = APIRouter(tags=['modelruns'])


@router.get("/modelruns/{modelrun_id}/eventcounts")
async def get_modelrun_rates(db: DBSessionDep,
                             modelrun_id: UUID,
                             min_lon: float,
                             min_lat: float,
                             res_lon: float,
                             res_lat: float,
                             max_lon: float,
                             max_lat: float,
                             realization_id: bool = False
                             ):

    # Execute the query
    stmt = text(EVENTCOUNTS).bindparams(modelrun_oid=modelrun_id,
                                        min_lon=min_lon + (res_lon / 2),
                                        min_lat=min_lat + (res_lat / 2),
                                        max_lon=max_lon,
                                        max_lat=max_lat,
                                        res_lon=res_lon,
                                        res_lat=res_lat)
    result = await db.execute(stmt)
    rows = result.fetchall()  # Fetch all results
    columns = result.keys()   # Get column names

    # Convert to Pandas DataFrame
    df = pd.DataFrame(rows, columns=columns)
    df['grid_lat'] = np.round(df['grid_lat'], 6)
    df['grid_lon'] = np.round(df['grid_lon'], 6)

    # make sure that all the lon and lat values are at least
    # once in the df so that the grid is complete
    bg_lons = np.round(np.arange(min_lon + (res_lon / 2),
                       max_lon, res_lon), 6)
    bg_lats = np.round(np.arange(min_lat + (res_lat / 2),
                       max_lat, res_lat), 6)

    missing_lon = list(set(bg_lons) - set(df['grid_lon']))
    missing_lat = list(set(bg_lats) - set(df['grid_lat']))

    # shorter = min(missing_lon, missing_lat, key=len)
    missing_lon.append(bg_lons[-1])
    missing_lat.append(bg_lats[-1])

    fillvalue = min(missing_lon, missing_lat, key=len)[-1]
    zipped = list(itertools.zip_longest(
        missing_lon[:-1], missing_lat[:-1], fillvalue=fillvalue))

    df = pd.concat([df, pd.DataFrame(
        [{'grid_lon': lon, 'grid_lat': lat, 'count': 0}
         for lon, lat in zipped])], ignore_index=True)

    # return a csv
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)

    csv_content = csv_buffer.getvalue()
    return Response(content=csv_content, media_type="text")


@router.get("/modelruns/{modelrun_id}/input")
async def get_modelrun_input(db: DBSessionDep, modelrun_id: UUID):
    """
    Returns an archive containing the input data for a modelrun.
    """

    # get the corresponding forecast
    forecast = await crud.read_forecast_by_modelrun(db, modelrun_id)

    if not forecast:
        raise HTTPException(status_code=404, detail="No modelrun not found.")

    forecast = ForecastSchema.model_validate(forecast)

    # get the corresponding forecastseries
    forecastseries = await crud.read_forecastseries(
        db, forecast.forecastseries_oid)
    forecastseries = ForecastSeriesSchema.model_validate(forecastseries)

    # get the corresponding modelconfig
    modelconfig = await crud.read_modelrun_modelconfig(db, modelrun_id)

    seismicityobservation = None
    if forecastseries.seismicityobservation_required != EInput.NOT_ALLOWED:
        seismicityobservation = await crud.read_forecast_seismicityobservation(
            db, forecast.oid)
        seismicityobservation = io.BytesIO(seismicityobservation)
        seismicityobservation.name = "seismicityobservation.xml"

    injectionobservation = None
    if forecastseries.injectionobservation_required != EInput.NOT_ALLOWED:
        injectionobservation = await crud.read_forecast_injectionobservation(
            db, forecast.oid)
        injectionobservation = io.BytesIO(injectionobservation)
        injectionobservation.name = "injectionobservation.json"

    injectionplan = None
    if forecastseries.injectionplan_required != EInput.NOT_ALLOWED:
        injectionplan = await crud.read_injectionplan_by_modelrun(
            db, modelrun_id)
        injectionplan = io.BytesIO(injectionplan)
        injectionplan.name = "injectionplan.json"

    model_input = ModelInput(
        forecast_start=forecast.starttime,
        forecast_end=forecast.endtime,
        bounding_polygon=forecastseries.bounding_polygon,
        depth_min=forecastseries.depth_min,
        depth_max=forecastseries.depth_max,
        model_parameters=modelconfig.model_parameters,
        model_settings=forecastseries.model_settings,
    )

    model_input = model_input.model_dump()
    model_input['sfm_module'] = modelconfig.sfm_module
    model_input['sfm_function'] = modelconfig.sfm_function
    model_input['injectionplan'] = bool(injectionplan)
    model_input['seismicityobservation'] = bool(seismicityobservation)
    model_input['injectionobservation'] = bool(injectionobservation)

    with open(Path(__file__).parent / 'templates/run_model.j2', 'r') as f:
        template = Template(f.read())

    run_file = io.StringIO(template.render({"data": model_input}))

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("run_model.py", run_file.read().encode("utf-8"))
        if seismicityobservation:
            zip_file.writestr(seismicityobservation.name,
                              seismicityobservation.read())
        if injectionobservation:
            zip_file.writestr(injectionobservation.name,
                              injectionobservation.read())
        if injectionplan:
            zip_file.writestr(injectionplan.name, injectionplan.read())

    # Step 3: Prepare the ZIP file for download
    zip_buffer.seek(0)  # Reset buffer pointer to the beginning
    headers = {"Content-Disposition": "attachment; filename=files.zip"}

    return StreamingResponse(zip_buffer,
                             media_type="application/zip",
                             headers=headers)


@router.get("/modelruns/{modelrun_id}/result")
async def get_modelrun_result(db: DBSessionDep, modelrun_id: UUID):
    """
    Returns the results of the modelrun.
    """
    # get modelrun result type
    modelconfig = await crud.read_modelrun_modelconfig(db, modelrun_id)
    result_type = modelconfig.result_type

    if result_type == EResultType.GRID:
        result = await crud.read_modelrun_rates(db, modelrun_id)
        result = ModelRunRateGridSchema.model_validate(result)
        result = result.model_dump(exclude_none=True)['rateforecasts']
        result = pd.json_normalize(result, sep='_')
        result.columns = result.columns.str.replace('_value', '')

    if result_type == EResultType.CATALOG:
        result = await crud.read_modelrun_catalog(db, modelrun_id)
        result = ModelRunCatalogSchema.model_validate(result)
        result = result.model_dump(exclude_none=True)[
            'catalogs']
        events = []
        for ri, r in enumerate(result):
            for ei, event in enumerate(r['seismicevents']):
                event['realization_id'] = r['realization_id']
            events.extend(result[ri]['seismicevents'])
        result = pd.json_normalize(events, sep='_')
        result.columns = result.columns.str.replace('_value', '')

    csv_buffer = io.StringIO()
    result.to_csv(csv_buffer, index=False)

    csv_content = csv_buffer.getvalue()
    return Response(content=csv_content, media_type="text")
