from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from hermes.repositories.project import ModelConfigRepository
from hermes.schemas.model_schemas import ModelConfig
from web.database import DBSessionDep

router = APIRouter(tags=['modelconfigs'])


@router.get("/modelconfigs",
            response_model=list[ModelConfig],
            response_model_exclude_none=True)
async def get_forecastseries_modelconfigs(
        db: DBSessionDep,
        tags: Annotated[list[str] | None, Query()] = None):
    """
    Returns a list of ModelConfigs
    """
    print(tags)
    if tags is None:
        db_result = await ModelConfigRepository.get_all_async(db)
    else:
        db_result = await ModelConfigRepository.get_by_tags_async(db, tags)

    return db_result


@router.get("/modelconfigs/{modelconfig_oid}",
            response_model=ModelConfig,
            response_model_exclude_none=True)
async def get_modelconfig(db: DBSessionDep,
                          modelconfig_oid: UUID):
    """
    Returns a ModelConfig
    """

    db_result = await ModelConfigRepository.get_by_id_async(db,
                                                            modelconfig_oid)

    if not db_result:
        raise HTTPException(status_code=404, detail="Modelconfig not found.")

    return db_result
