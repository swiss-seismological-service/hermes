from uuid import UUID

from fastapi import APIRouter, HTTPException

from hermes.repositories.project import ModelConfigRepository
from hermes.schemas.model_schemas import ModelConfig
from web.database import DBSessionDep

router = APIRouter(tags=['modelruns'])


@router.get("/modelruns/{modelrun_oid}/modelconfig",
            response_model=ModelConfig,
            response_model_exclude_none=False)
async def get_modelrun_modelconfig(db: DBSessionDep, modelrun_oid: UUID):

    db_result = await ModelConfigRepository.get_by_modelrun_async(
        db, modelrun_oid)

    if not db_result:
        raise HTTPException(
            status_code=404, detail="No modelrun or ModelConfig found.")

    return db_result


# @router.get("/modelruns/{modelrun_id}/rates",
#             response_model=ModelRunRateGridSchema,
#             response_model_exclude_none=True)
# async def get_modelrun_rates(db: DBSessionDep, modelrun_id: UUID):
#     db_result = await crud.read_modelrun_rates(db,
#                                                modelrun_id)
#     if not db_result:
#         raise HTTPException(status_code=404, detail="No modelrun found.")

#     return db_result
