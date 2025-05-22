from uuid import UUID

from fastapi import APIRouter, HTTPException, Response

from web.repositories.data import (AsyncInjectionObservationRepository,
                                   AsyncInjectionPlanRepository)
from web.repositories.database import DBSessionDep
from web.schemas import InjectionPlanJSON

router = APIRouter(tags=['injections'])


@router.get("/injectionplans/{injectionplan_oid}",
            response_class=Response)
async def get_modelconfig(db: DBSessionDep,
                          injectionplan_oid: UUID):
    """
    Returns a ModelConfig
    """

    db_result = await AsyncInjectionPlanRepository.get_by_id(db,
                                                             injectionplan_oid)

    if not db_result:
        raise HTTPException(status_code=404,
                            detail="InjectionPlan not found.")

    if db_result.data is None:
        raise HTTPException(status_code=404,
                            detail="InjectionPlan data not found.")

    return Response(db_result.data[1:-1],  # remove start and end []
                    media_type='application/json')


@router.get("/injectionplantemplates/{injectionplan_oid}",
            response_model=InjectionPlanJSON,
            response_model_exclude_none=True)
async def get_injectionplan_template(db: DBSessionDep,
                                     injectionplan_oid: UUID):
    """
    Returns a InjectionPlan template
    """
    db_result = await AsyncInjectionPlanRepository.get_by_id(db,
                                                             injectionplan_oid)
    if not db_result:
        raise HTTPException(status_code=404,
                            detail="InjectionPlan not found.")
    return db_result


@router.get("/injectionobservations/{injectionobservation_oid}",
            response_class=Response)
async def get_injection_observations(db: DBSessionDep,
                                     injectionobservation_oid: UUID):
    """
    Returns a InjectionObservation
    """
    db_result = await AsyncInjectionObservationRepository.get_by_id(
        db,
        injectionobservation_oid)

    if not db_result:
        raise HTTPException(status_code=404,
                            detail="InjectionObservation not found.")

    return Response(db_result.data,
                    media_type='application/json')
