import io
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Response
from sqlalchemy import text

from web.database import DBSessionDep
from web.routers.v2.queries.forecastseries import EVENT_COUNT_SERIES

router = APIRouter(tags=['forecastseries'])


@router.get("/forecastseries/{forecastseries_oid}/eventcounts")
async def get_forecastseries_eventcounts(
        db: DBSessionDep,
        forecastseries_oid: UUID,
        modelconfig_oid: UUID,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float):
    """
    Returns the seismicity observation for a given forecast.
    """
    stmt = text(EVENT_COUNT_SERIES).bindparams(
        forecastseries_oid=forecastseries_oid,
        modelconfig_oid=modelconfig_oid,
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
    )

    result = await db.execute(stmt)
    rows = result.fetchall()  # Fetch all results
    columns = result.keys()   # Get column names

    df = pd.DataFrame(rows, columns=columns)

    # return a csv
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)

    csv_content = csv_buffer.getvalue()
    return Response(content=csv_content, media_type="text")
