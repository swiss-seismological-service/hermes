import io
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import text

from hermes.repositories.data import InjectionPlanRepository
from hermes.repositories.project import (ForecastRepository,
                                         ForecastSeriesRepository,
                                         ModelConfigRepository)
from hermes.schemas.base import EResultType
from hermes.schemas.model_schemas import ModelConfig
from hermes.schemas.web_schemas import (ForecastJSON, ForecastSeriesJSON,
                                        InjectionPlanJSON)
from web.database import DBSessionDep
from web.queries.forecastseries import EVENT_COUNT_SERIES

router = APIRouter(prefix='/forecastseries', tags=['forecastseries'])


@router.get("/{forecastseries_oid}",
            response_model=ForecastSeriesJSON,
            response_model_exclude_none=True)
async def get_forecastseries(db: DBSessionDep,
                             forecastseries_oid: UUID):
    """
    Returns a ForecastSeries
    """

    db_result = await ForecastSeriesRepository.get_by_id_async(
        db, forecastseries_oid, joined_attrs=['_tags', 'injectionplans'],
        override_model=ForecastSeriesJSON)

    if not db_result:
        raise HTTPException(status_code=404, detail="No forecastseries found.")

    db_result.modelconfigs = await ModelConfigRepository.get_by_tags_async(
        db, db_result.tags)

    return db_result


@router.get("/{forecastseries_oid}/forecasts",
            response_model=list[ForecastJSON],
            response_model_exclude_none=True)
async def get_forecasts(db: DBSessionDep,
                        forecastseries_oid: UUID):
    """
    Returns a list of ForecastSeries
    """
    db_result = await ForecastRepository.get_by_forecastseries_joined_async(
        db, forecastseries_oid)

    return db_result


@router.get("/{forecastseries_oid}/modelconfigs",
            response_model=list[ModelConfig],
            response_model_exclude_none=True)
async def get_modelconfigs(db: DBSessionDep,
                           forecastseries_oid: UUID):
    """
    Returns a list of ModelConfigs
    """

    fs = await ForecastSeriesRepository.get_by_id_async(
        db, forecastseries_oid)

    if not fs:
        raise HTTPException(status_code=404, detail="No forecastseries found.")

    db_result = await ModelConfigRepository.get_by_tags_async(
        db, fs.tags)

    return db_result


@router.get("/{forecastseries_oid}/injectionplans",
            response_model=list[InjectionPlanJSON],
            response_model_exclude_none=True)
async def get_injectionplans(db: DBSessionDep,
                             forecastseries_oid: UUID):
    """
    Returns a list of InjectionPlans
    """

    db_result = await InjectionPlanRepository.get_by_forecastseries_async(
        db, forecastseries_oid)

    return db_result


@router.get("/{forecastseries_oid}/eventcounts")
async def get_gridded_evencounts(
        db: DBSessionDep,
        forecastseries_oid: UUID,
        modelconfig_oid: UUID,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float):
    """
    Returns the seismicity observation for a given forecast.
    """

    # TODO: Improve performance if possible
    # TODO: Automatic grid bounds if not provided

    # Check for correct result type
    config = await ModelConfigRepository.get_by_id_async(db, modelconfig_oid)
    if config.result_type != EResultType.CATALOG:
        return HTTPException(400, "Wrong result type for this endpoint.")

    stmt = text(EVENT_COUNT_SERIES).bindparams(
        forecastseries_oid=forecastseries_oid,
        modelconfig_oid=modelconfig_oid,
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
    )

    result = await db.execute(stmt)
    rows = result.fetchall()  # Fetch all results
    columns = result.keys()   # Get column names

    df = pd.DataFrame(rows, columns=columns)

    # return a csv
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)

    csv_content = csv_buffer.getvalue()
    return Response(content=csv_content, media_type="text")
