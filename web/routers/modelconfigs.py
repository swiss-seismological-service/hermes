from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from hermes.schemas.model_schemas import ModelConfig
from web.repositories.database import DBSessionDep
from web.repositories.project import AsyncModelConfigRepository

router = APIRouter(prefix='/modelconfigs', tags=['modelconfigs'])


@router.get("",
            response_model=list[ModelConfig],
            response_model_exclude_none=True)
async def get_all_modelconfigs(
        db: DBSessionDep,
        tags: Annotated[list[str] | None, Query()] = None):
    """
    Returns a list of ModelConfigs
    """

    if tags is None:
        db_result = await AsyncModelConfigRepository.get_all(db)
    else:
        db_result = await AsyncModelConfigRepository.get_by_tags(db, tags)

    return db_result


@router.get("/{modelconfig_oid}",
            response_model=ModelConfig,
            response_model_exclude_none=True)
async def get_modelconfig(db: DBSessionDep,
                          modelconfig_oid: UUID):
    """
    Returns a ModelConfig
    """

    db_result = await AsyncModelConfigRepository.get_by_id(db,
                                                           modelconfig_oid)

    if not db_result:
        raise HTTPException(status_code=404, detail="Modelconfig not found.")

    return db_result
