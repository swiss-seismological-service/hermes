import io
import zipfile
from pathlib import Path
from uuid import UUID

import pandas as pd
from fastapi import APIRouter
from fastapi.responses import Response, StreamingResponse
from hermes_model import ModelInput
from jinja2 import Template

from hermes.schemas.base import EInput, EResultType
from web import crud
from web.database import DBSessionDep
from web.schemas import (ForecastDetailSchema, ForecastSchema,
                         ForecastSeriesSchema, ModelRunCatalogSchema,
                         ModelRunRateGridSchema)

router = APIRouter()


@router.get("/forecasts",
            response_model=list[ForecastDetailSchema],
            response_model_exclude_none=False)
async def get_forecasts(db: DBSessionDep):
    """
    Returns the last 100 forecasts.
    """
    db_result = await crud.read_forecasts(db)
    return db_result


@router.get("/modelruns/{modelrun_id}/input")
async def get_modelrun_input(db: DBSessionDep, modelrun_id: UUID):
    """
    Returns an archive containing the input data for a modelrun.
    """

    # get the corresponding forecast
    forecast = await crud.read_forecast_by_modelrun(db, modelrun_id)
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

    # csv_buffer.seek(0)
    # headers = {"Content-Disposition": "attachment; filename=dataframe.csv"}

    # return StreamingResponse(csv_buffer,
    #                          media_type="text/csv",
    #                           headers=headers
    #                          )

    csv_content = csv_buffer.getvalue()
    return Response(content=csv_content, media_type="text")
