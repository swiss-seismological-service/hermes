from uuid import UUID

from fastapi import APIRouter, HTTPException

from hermes.repositories.project import ProjectRepository
from web.database import DBSessionDep
from web.schemas import ProjectJSON

router = APIRouter(prefix='/projects', tags=['project'])


@router.get("",
            response_model=list[ProjectJSON],
            response_model_exclude_none=False)
async def get_all_projects(db: DBSessionDep):
    """
    Returns a list of projects.
    """
    db_result = await ProjectRepository.get_all_async(db)

    if not db_result:
        raise HTTPException(status_code=404, detail="No projects found.")

    return db_result


@router.get("/{project_oid}",
            response_model=ProjectJSON,
            response_model_exclude_none=False)
async def get_project(db: DBSessionDep,
                      project_oid: UUID):
    """
    Returns a projects by id.
    """
    # db_result = await crud.read_project(db, project_oid)
    db_result = await ProjectRepository.get_by_id_async(db, project_oid)

    if not db_result:
        raise HTTPException(status_code=404, detail="No projects found.")

    return db_result
