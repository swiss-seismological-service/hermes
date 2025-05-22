from uuid import UUID

from fastapi import APIRouter, HTTPException

from hermes.repositories.project import (ForecastSeriesRepository,
                                         ModelConfigRepository,
                                         ProjectRepository)
from hermes.schemas.web_schemas import ForecastSeriesJSON, ProjectJSON
from web.database import DBSessionDep

router = APIRouter(prefix='/projects', tags=['project'])


@router.get("",
            response_model=list[ProjectJSON],
            response_model_exclude_none=True)
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
            response_model_exclude_none=True)
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


@router.get("/{project_id}/forecastseries",
            response_model=list[ForecastSeriesJSON],
            response_model_exclude_none=True)
async def get_projects_forecastseries(db: DBSessionDep,
                                      project_id: UUID):
    """
    Returns a list of ForecastSeries
    """

    db_result = await ForecastSeriesRepository.get_by_project_async(
        db, project_id, joined_attrs=['_tags', 'injectionplans'],
        override_model=ForecastSeriesJSON)

    if not db_result:
        raise HTTPException(status_code=404, detail="No forecastseries found.")

    for fc in db_result:
        fc.modelconfigs = await ModelConfigRepository.get_by_tags_async(
            db, fc.tags)

    return db_result
