from uuid import UUID

from fastapi import APIRouter, HTTPException

from web.repositories.database import DBSessionDep
from web.repositories.project import (AsyncForecastSeriesRepository,
                                      AsyncModelConfigRepository,
                                      AsyncProjectRepository)
from web.schemas import ForecastSeriesJSON, ProjectJSON

router = APIRouter(prefix='/projects', tags=['project'])


@router.get("",
            response_model=list[ProjectJSON],
            response_model_exclude_none=True)
async def get_all_projects(db: DBSessionDep):
    """
    Returns a list of projects.
    """
    db_result = await AsyncProjectRepository.get_all(db)

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
    db_result = await AsyncProjectRepository.get_by_id(db, project_oid)

    if not db_result:
        raise HTTPException(status_code=404, detail="Project not found.")

    return db_result


@router.get("/{project_id}/forecastseries",
            response_model=list[ForecastSeriesJSON],
            response_model_exclude_none=True)
async def get_projects_forecastseries(db: DBSessionDep,
                                      project_id: UUID):
    """
    Returns a list of ForecastSeries
    """

    db_result = await AsyncForecastSeriesRepository.get_by_project(
        db, project_id, joined_attrs=['_tags', 'injectionplans'],
        override_model=ForecastSeriesJSON)

    for fc in db_result:
        fc.modelconfigs = await AsyncModelConfigRepository.get_by_tags(
            db, fc.tags)

    return db_result
