import json
from datetime import datetime
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, HTTPException, Response
from seismostats import Catalog
from sqlalchemy import text

from hermes.repositories.data import InjectionObservationRepository
from hermes.repositories.project import ForecastRepository
from hermes.repositories.results import ModelRunRepository
from hermes.schemas.result_schemas import ModelRun
from web.database import DBSessionDep
from web.queries.forecasts import OBSERVED_EVENTS
from web.schemas import ForecastSchema

router = APIRouter(tags=['forecast'])


@router.get("/forecastseries/{forecastseries_oid}/forecasts",
            response_model=list[ForecastSchema],
            response_model_exclude_none=False)
async def get_all_forecasts(db: DBSessionDep,
                            forecastseries_oid: UUID):
    """
    Returns a list of ForecastSeries
    """

    db_result = await ForecastRepository.get_by_forecastseries_async(
        db, forecastseries_oid)

    if not db_result:
        raise HTTPException(status_code=404, detail="No forecastseries found.")

    return db_result


@router.get("/forecasts/{forecast_oid}",
            response_model=ForecastSchema,
            response_model_exclude_none=False)
async def get_forecast(db: DBSessionDep,
                       forecast_oid: UUID):
    """
    Returns a single Forecast
    """

    db_result = await ForecastRepository.get_by_id_async(
        db, forecast_oid)

    if not db_result:
        raise HTTPException(status_code=404, detail="No forecast found.")

    return db_result


@router.get("/forecasts/{forecast_oid}/injectionobservations",
            responses={
                200: {
                    "content": {"application/json": {}},
                    "description": "Return the HYDWS JSON.",
                }
            })
async def get_forecast_injectionobservation(
        db: DBSessionDep, forecast_oid: UUID):

    db_result = await InjectionObservationRepository.get_by_forecast_async(
        db, forecast_oid)

    if not db_result:
        raise HTTPException(
            status_code=404,
            detail="No Forecast or injectionobservation found.")

    db_result = db_result.model_dump()
    if 'data' in db_result.keys():
        db_result['data'] = json.loads(db_result['data'])

    return Response(
        content=json.dumps(db_result['data']),
        media_type="application/json")


@router.get("/forecasts/{forecast_id}/seismicityobservation")
async def get_forecast_seismicityobservation(
        db: DBSessionDep,
        forecast_id: UUID,
        start_time: datetime,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        min_mag: float,
        end_time: datetime = datetime.now()):
    """
    Returns the seismicity observation for a given forecast.
    """
    stmt = text(OBSERVED_EVENTS).bindparams(
        forecast_id=forecast_id,
        start_time=start_time,
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
        min_mag=min_mag,
        end_time=end_time
    )

    result = await db.execute(stmt)
    rows = result.fetchall()  # Fetch all results
    columns = result.keys()   # Get column names

    cat = pd.DataFrame(rows, columns=columns)
    cat = Catalog(cat.rename(columns=lambda col:
                             col.removesuffix('_value')))
    qml = cat.to_quakeml()
    return Response(content=qml,
                    media_type="application/xml")


@router.get("/forecasts/{forecast_oid}/modelruns",
            response_model=list[ModelRun])
async def get_forecast_modelruns(db: DBSessionDep,
                                 forecast_oid: UUID):
    """
    Returns a list of ModelRuns for this forecast.
    """
    db_result = await ModelRunRepository.get_by_forecast_async(
        db, forecast_oid)

    return db_result
