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

from hermes.repositories.data import (InjectionObservationRepository,
                                      InjectionPlanRepository,
                                      SeismicityObservationRepository)
from hermes.repositories.project import (ForecastRepository,
                                         ForecastSeriesRepository,
                                         ModelConfigRepository)
from hermes.repositories.results import GRParametersRepository
from hermes.schemas.base import EInput, EResultType
from hermes.schemas.model_schemas import ModelConfig
from web.database import DBSessionDep
from web.queries.modelruns import EVENTCOUNTS
from web.schemas import ForecastSchema

router = APIRouter(tags=['modelruns'])


@router.get("/modelruns/{modelrun_oid}/modelconfig",
            response_model=ModelConfig,
            response_model_exclude_none=False)
async def get_modelrun_modelconfig(db: DBSessionDep, modelrun_oid: UUID):

    db_result = await ModelConfigRepository.get_by_modelrun_async(
        db, modelrun_oid)

    if not db_result:
        raise HTTPException(
            status_code=404, detail="No modelrun or ModelConfig found.")

    return db_result


@router.get("/modelruns/{modelrun_id}/eventcounts")
async def get_modelrun_rates(db: DBSessionDep,
                             modelrun_id: UUID,
                             min_lon: float,
                             min_lat: float,
                             res_lon: float,
                             res_lat: float,
                             max_lon: float,
                             max_lat: float
                             ):

    # Check for correct result type
    config = await ModelConfigRepository.get_by_modelrun_async(db, modelrun_id)
    if config.result_type != EResultType.CATALOG:
        return HTTPException(400, "Wrong result type for this endpoint.")

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
    forecast = await ForecastRepository.get_by_modelrun_async(
        db, modelrun_id)
    if not forecast:
        raise HTTPException(status_code=404, detail="No modelrun not found.")

    forecast = ForecastSchema.model_validate(forecast)

    # get the corresponding forecastseries
    forecastseries = await ForecastSeriesRepository.get_by_id_async(
        db,
        forecast.forecastseries_oid)

    # get the corresponding modelconfig
    modelconfig = await ModelConfigRepository.get_by_modelrun_async(
        db, modelrun_id)
    seismicityobservation = None
    if forecastseries.seismicityobservation_required != EInput.NOT_ALLOWED:
        seismicityobservation = \
            await SeismicityObservationRepository.get_by_forecast_async(
                db, forecast.oid)
        seismicityobservation = io.BytesIO(seismicityobservation.data)
        seismicityobservation.name = "seismicityobservation.xml"

    injectionobservation = None
    if forecastseries.injectionobservation_required != EInput.NOT_ALLOWED:
        injectionobservation = \
            await InjectionObservationRepository.get_by_forecast_async(
                db, forecast.oid)
        injectionobservation = io.BytesIO(injectionobservation.data)
        injectionobservation.name = "injectionobservation.json"

    injectionplan = None
    if forecastseries.injectionplan_required != EInput.NOT_ALLOWED:
        injectionplan = await InjectionPlanRepository.get_by_modelrun_async(
            db, modelrun_id)
        injectionplan = injectionplan.data
        injectionplan = io.BytesIO(injectionplan)
        injectionplan.name = "injectionplan.json"

    model_input = ModelInput(
        forecast_start=forecast.starttime,
        forecast_end=forecast.endtime,
        bounding_polygon=forecastseries.bounding_polygon.wkt,
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


@router.get("/modelruns/{modelrun_id}/forecast")
async def get_modelrun_forecast(db: DBSessionDep, modelrun_id: UUID):
    """
    Returns the forecast data for a modelrun.
    """

    modelconfig = await ModelConfigRepository.get_by_modelrun_async(
        db, modelrun_id)

    if modelconfig.result_type == EResultType.GRID:
        forecast = await GRParametersRepository.get_forecast_grrategrid(
            db,
            modelrun_id)
        if forecast.empty:
            raise HTTPException(status_code=404,
                                detail="No forecast data found.")
    else:
        raise NotImplementedError

    # return a csv
    csv_buffer = io.StringIO()
    forecast.to_csv(csv_buffer, index=False)

    csv_content = csv_buffer.getvalue()
    return Response(content=csv_content, media_type="text")
