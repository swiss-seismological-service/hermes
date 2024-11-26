from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response

from web import crud
from web.database import DBSessionDep
from web.routers import XMLResponse
from web.schemas import (ForecastDetailSchema, ForecastSchema,
                         ModelRunRateGridSchema)

router = APIRouter(tags=['forecast'])


@router.get("/forecastseries/{forecastseries_oid}/forecasts",
            response_model=list[ForecastSchema],
            response_model_exclude_none=False)
async def get_all_forecasts(db: DBSessionDep,
                            forecastseries_oid: UUID):
    """
    Returns a list of ForecastSeries
    """

    db_result = await crud.read_all_forecasts(db, forecastseries_oid)

    if not db_result:
        raise HTTPException(status_code=404, detail="No forecastseries found.")

    return db_result


@router.get("/forecasts/{forecast_oid}",
            response_model=ForecastDetailSchema,
            response_model_exclude_none=False)
async def get_forecast(db: DBSessionDep,
                       forecast_oid: UUID):
    """
    Returns a single Forecast
    """

    db_result = await crud.read_forecast_modelruns(db, forecast_oid)

    if not db_result:
        raise HTTPException(status_code=404, detail="No forecast found.")

    return db_result


@router.get("/forecasts/{forecast_oid}/injectionwells",
            responses={
                200: {
                    "content": {"application/json": {}},
                    "description": "Return the HYDWS JSON.",
                }
            })
async def get_forecast_injectionwell(db: DBSessionDep, forecast_oid: UUID):

    db_result = await crud.read_forecast_injectionwells(db, forecast_oid)

    if not db_result:
        raise HTTPException(
            status_code=404, detail="No Forecast or InjectionWells found.")

    return Response(
        content=db_result,
        media_type="application/json")


@router.get("/forecasts/{forecast_oid}/seismiccatalog",
            responses={
                200: {
                    "content": {"application/xml": {}},
                    "description": "Return the seismic catalog as QML.",
                }
            },
            response_class=XMLResponse)
async def get_forecast_seismiccatalog(db: DBSessionDep,
                                      forecast_oid: UUID):
    """
    Returns the seismic catalog for this project.
    """
    db_result = await crud.read_forecast_seismiccatalog(db, forecast_oid)

    if not db_result:
        raise HTTPException(
            status_code=404,
            detail="No Forecast or SeismicityObservation found.")

    return Response(
        content=db_result,
        media_type="application/xml")


@router.get("/forecasts/{forecast_id}/rates",
            response_model=list[ModelRunRateGridSchema],
            response_model_exclude_none=True)
async def get_forecast_rates(
        db: DBSessionDep,
        forecast_id: UUID,
        modelconfigs: Annotated[list[str] | None, Query()] = None,
        injectionplans: Annotated[list[str] | None, Query()] = None):
    """
    Returns a list of ForecastRateGrids
    """
    db_result = await crud.read_forecast_rates(db,
                                               forecast_id,
                                               modelconfigs,
                                               injectionplans)

    if not db_result:
        raise HTTPException(status_code=404, detail="No forecast found.")

    return db_result
