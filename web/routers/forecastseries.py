

from uuid import UUID

from fastapi import APIRouter, HTTPException

from web import crud
from web.database import DBSessionDep
from web.schemas import ForecastSeriesSchema, ModelConfigNameSchema

router = APIRouter(tags=['forecastseries'])


@router.get("/projects/{project_id}/forecastseries",
            response_model=list[ForecastSeriesSchema],
            response_model_exclude_none=True)
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
