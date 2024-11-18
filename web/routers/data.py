from uuid import UUID

from fastapi import APIRouter, HTTPException, Response

from web import crud
from web.database import DBSessionDep

router = APIRouter(tags=['data'])


@router.get("/injectionplans/{injectionplan_oid}",
            responses={
                200: {
                    "content": {"application/json": [{}]},
                    "description": "Return the injection plan as JSON.",
                }
            })
async def get_injectionplan(db: DBSessionDep, injectionplan_oid: UUID):

    db_result = await crud.read_injectionplan(db, injectionplan_oid)

    if not db_result:
        raise HTTPException(status_code=404, detail="No injection plan found.")

    return Response(
        content=db_result,
        media_type="application/json")
