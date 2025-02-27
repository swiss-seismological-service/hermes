from datetime import datetime
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Response
from seismostats import Catalog
from sqlalchemy import text

from web import crud
from web.database import DBSessionDep
from web.routers.v2.queries.forecasts import OBSERVED_EVENTS
from web.schemas import ForecastDetailSchema

router = APIRouter(tags=['forecast'])


@router.get("/forecasts",
            response_model=list[ForecastDetailSchema],
            response_model_exclude_none=False)
async def get_forecasts(db: DBSessionDep):
    """
    Returns the last 100 forecasts.
    """
    db_result = await crud.read_forecasts(db)
    return db_result


@router.get("/forecasts/{forecast_id}/seismicityobservation")
async def get_forecast_seismicityobservation(
        db: DBSessionDep,
        forecast_id: UUID,
        start_time: datetime,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        min_mag: float,
        end_time: datetime = datetime.now()):
    """
    Returns the seismicity observation for a given forecast.
    """
    stmt = text(OBSERVED_EVENTS).bindparams(
        forecast_id=forecast_id,
        start_time=start_time,
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
        min_mag=min_mag,
        end_time=end_time
    )

    result = await db.execute(stmt)
    rows = result.fetchall()  # Fetch all results
    columns = result.keys()   # Get column names

    cat = pd.DataFrame(rows, columns=columns)
    cat = Catalog(cat.rename(columns=lambda col:
                             col.removesuffix('_value')))
    qml = cat.to_quakeml()
    return Response(content=qml,
                    media_type="application/xml")
