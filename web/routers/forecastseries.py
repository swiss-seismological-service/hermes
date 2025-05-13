import io
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import text

from hermes.repositories.data import InjectionPlanRepository
from hermes.repositories.project import (ForecastSeriesRepository,
                                         ModelConfigRepository)
from hermes.schemas.model_schemas import ModelConfig
from web.database import DBSessionDep
from web.queries.forecastseries import EVENT_COUNT_SERIES
from web.schemas import ForecastSeriesJSONSchema, InjectionPlanSchema

router = APIRouter(tags=['forecastseries'])


@router.get("/projects/{project_id}/forecastseries",
            response_model=list[ForecastSeriesJSONSchema],
            response_model_exclude_none=True)
async def get_all_forecastseries(db: DBSessionDep,
                                 project_id: UUID):
    """
    Returns a list of ForecastSeries
    """

    db_result = await ForecastSeriesRepository.get_by_project_async(
        db, project_id, joined_attrs=['_tags', 'injectionplans'],
        override_model=ForecastSeriesJSONSchema)

    if not db_result:
        raise HTTPException(status_code=404, detail="No forecastseries found.")

    for fc in db_result:
        fc.modelconfigs = await ModelConfigRepository.get_by_tags_async(
            db, fc.tags)

    return db_result


@router.get("/forecastseries/{forecastseries_oid}",
            response_model=ForecastSeriesJSONSchema,
            response_model_exclude_none=True)
async def get_forecastseries(db: DBSessionDep,
                             forecastseries_oid: UUID):
    """
    Returns a ForecastSeries
    """

    db_result = await ForecastSeriesRepository.get_by_id_async(
        db, forecastseries_oid, joined_attrs=['_tags', 'injectionplans'],
        override_model=ForecastSeriesJSONSchema)

    if not db_result:
        raise HTTPException(status_code=404, detail="No forecastseries found.")

    db_result.modelconfigs = await ModelConfigRepository.get_by_tags_async(
        db, db_result.tags)

    return db_result


@router.get("/forecastseries/{forecastseries_oid}/modelconfigs",
            response_model=list[ModelConfig],
            response_model_exclude_none=True)
async def get_forecastseries_modelconfigs(db: DBSessionDep,
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

    if not db_result:
        raise HTTPException(status_code=404, detail="No modelconfigs found.")

    return db_result


@router.get("/forecastseries/{forecastseries_oid}/injectionplans",
            response_model=list[InjectionPlanSchema],
            response_model_exclude_none=True)
async def get_forecastseries_injectionplans(db: DBSessionDep,
                                            forecastseries_oid: UUID):
    """
    Returns a list of InjectionPlans
    """

    db_result = await InjectionPlanRepository.get_by_forecastseries_async(
        db, forecastseries_oid)

    if not db_result:
        raise HTTPException(status_code=404, detail="No injectionplans found.")

    return db_result


@router.get("/forecastseries/{forecastseries_oid}/eventcounts")
async def get_forecastseries_eventcounts(
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
