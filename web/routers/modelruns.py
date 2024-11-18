from uuid import UUID

from fastapi import APIRouter, HTTPException

from hermes.schemas.model_schemas import ModelConfig
from web import crud
from web.database import DBSessionDep

router = APIRouter(tags=['modelruns'])


@router.get("/modelruns/{modelrun_oid}/modelconfig",
            response_model=ModelConfig,
            response_model_exclude_none=False)
async def get_modelrun_modelconfig(db: DBSessionDep, modelrun_oid: UUID):
    db_result = await crud.read_modelrun_modelconfig(db,
                                                     modelrun_oid)

    if not db_result:
        raise HTTPException(
            status_code=404, detail="No modelrun or ModelConfig found.")

    return db_result
