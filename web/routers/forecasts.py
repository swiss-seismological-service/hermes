from uuid import UUID

from fastapi import APIRouter, HTTPException

from web import crud
from web.database import DBSessionDep
from web.schemas import ForecastDetailSchema, ForecastSchema

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
    print(db_result)
    if not db_result:
        raise HTTPException(status_code=404, detail="No forecast found.")

    return db_result
