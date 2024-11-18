

from uuid import UUID

from fastapi import APIRouter, HTTPException

from hermes.schemas.model_schemas import ModelConfig
from web import crud
from web.database import DBSessionDep
from web.schemas import (ForecastSeriesSchema, InjectionPlanSchema,
                         ModelConfigNameSchema)

router = APIRouter(tags=['forecastseries'])


@router.get("/projects/{project_id}/forecastseries",
            response_model=list[ForecastSeriesSchema],
            response_model_exclude_none=False)
async def get_all_forecastseries(db: DBSessionDep,
                                 project_id: UUID):
    """
    Returns a list of ForecastSeries
    """

    db_result = await crud.read_all_forecastseries(db, project_id)

    for fc in db_result:

        model_configs = await crud.read_modelconfigs(
            db, fc.tags)

        modelconfigs = [ModelConfigNameSchema.model_validate(
            model) for model in model_configs]

        fc.modelconfigs = modelconfigs

    if not db_result:
        raise HTTPException(status_code=404, detail="No forecastseries found.")

    return db_result


@router.get("/forecastseries/{forecastseries_oid}",
            response_model=ForecastSeriesSchema,
            response_model_exclude_none=True)
async def get_forecastseries(db: DBSessionDep,
                             forecastseries_oid: UUID):
    """
    Returns a ForecastSeries
    """

    db_result = await crud.read_forecastseries(db, forecastseries_oid)

    if not db_result:
        raise HTTPException(status_code=404, detail="No forecastseries found.")

    model_configs = await crud.read_modelconfigs(db, db_result.tags)

    modelconfigs = [ModelConfigNameSchema.model_validate(
        model) for model in model_configs]

    db_result.modelconfigs = modelconfigs

    return db_result


@router.get("/forecastseries/{forecastseries_oid}/modelconfigs",
            response_model=list[ModelConfig],
            response_model_exclude_none=True)
async def get_forecastseries_modelconfigs(db: DBSessionDep,
                                          forecastseries_oid: UUID):
    """
    Returns a list of ModelConfigs
    """

    db_result = await crud.read_forecastseries_modelconfigs(
        db, forecastseries_oid)

    if not db_result:
        raise HTTPException(status_code=404, detail="No forecastseries found.")

    return db_result


@router.get("/forecastseries/{forecastseries_oid}/injectionplans",
            response_model=list[InjectionPlanSchema],
            response_model_exclude_none=True)
async def get_forecastseries_injectionplans(db: DBSessionDep,
                                            forecastseries_oid: UUID):
    """
    Returns a list of InjectionPlans
    """

    db_result = await crud.read_forecastseries_injectionplans(
        db, forecastseries_oid)

    if not db_result:
        raise HTTPException(status_code=404, detail="No forecastseries found.")

    return db_result
