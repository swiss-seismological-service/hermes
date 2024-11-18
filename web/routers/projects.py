from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException

from web import crud
from web.database import DBSessionDep
from web.schemas import ProjectSchema

router = APIRouter(prefix='/projects', tags=['project'])


@router.get("",
            response_model=list[ProjectSchema],
            response_model_exclude_none=False)
async def get_all_projects(db: DBSessionDep,
                           starttime: datetime | None = None):
    """
    Returns a list of projects.
    """
    db_result = await crud.read_all_projects(db, starttime)

    if not db_result:
        raise HTTPException(status_code=404, detail="No projects found.")

    return db_result


@router.get("/{project_oid}",
            response_model=ProjectSchema,
            response_model_exclude_none=False)
async def get_project(db: DBSessionDep,
                      project_oid: UUID):
    """
    Returns a projects by id.
    """
    db_result = await crud.read_project(db, project_oid)

    if not db_result:
        raise HTTPException(status_code=404, detail="No projects found.")

    return db_result
