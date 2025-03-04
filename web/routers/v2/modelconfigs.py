from uuid import UUID

from fastapi import APIRouter, HTTPException

from hermes.schemas.model_schemas import ModelConfig
from web import crud
from web.database import DBSessionDep

router = APIRouter(tags=['modelconfigs'])


@router.get("/modelconfigs",
            response_model=list[ModelConfig],
            response_model_exclude_none=True)
async def get_forecastseries_modelconfigs(db: DBSessionDep,
                                          tags: list[str] | None = None):
    """
    Returns a list of ModelConfigs
    """

    db_result = await crud.read_modelconfigs(db, tags)

    return db_result


@router.get("/modelconfigs/{modelconfig_oid}",
            response_model=ModelConfig,
            response_model_exclude_none=True)
async def get_modelconfig(db: DBSessionDep,
                          modelconfig_oid: UUID):
    """
    Returns a ModelConfig
    """

    db_result = await crud.read_modelconfig(db, modelconfig_oid)

    if not db_result:
        raise HTTPException(status_code=404, detail="Modelconfig not found.")

    return db_result
