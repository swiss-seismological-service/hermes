from datetime import datetime

from fastapi import APIRouter, HTTPException, Response

from hermes.schemas import Project
from web import crud
from web.database import DBSessionDep
from web.routers import XMLResponse

router = APIRouter(prefix='/projects', tags=['project'])


@router.get("",
            response_model=list[Project],
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


@router.get("/{project_id}",
            response_model=Project,
            response_model_exclude_none=False)
async def get_project(db: DBSessionDep,
                      project_id: int):
    """
    Returns a projects by id.
    """
    db_result = await crud.read_project(db, project_id)

    if not db_result:
        raise HTTPException(status_code=404, detail="No projects found.")

    return db_result


@router.get("/{project_id}/seismiccatalog",
            responses={
                200: {
                    "content": {"application/xml": {}},
                    "description": "Return the seismic catalog as QML.",
                }
            },
            response_class=XMLResponse)
async def get_project_seismiccatalog(db: DBSessionDep,
                                     project_id: int):
    """
    Returns the seismic catalog for this project.
    """
    db_result = await crud.read_project(db, project_id, True)

    if not db_result:
        raise HTTPException(status_code=404, detail="No projects found.")

    catalog = db_result.seismiccatalog

    return Response(
        content=catalog,
        media_type="application/xml")


@router.get("/{project_id}/injectionwell",
            responses={
                200: {
                    "content": {"application/json": {}},
                    "description": "Return the HYDWS JSON.",
                }
            })
async def get_project_injectionwell(db: DBSessionDep,
                                    project_id: int):
    """
    Returns the injection data for this project.
    """
    db_result = await crud.read_project(db, project_id, True)

    if not db_result:
        raise HTTPException(status_code=404, detail="No projects found.")

    well = db_result.injectionwell

    return Response(
        content=well,
        media_type="application/json")
