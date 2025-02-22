import io
import itertools
from uuid import UUID

import numpy as np
import pandas as pd
from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy import text

from web.database import DBSessionDep
from web.schemas import ModelRunRateGridSchema

QUERY1 = """
WITH grid_cells AS (
    SELECT ST_SnapToGrid(events.coordinates,
                        :min_lon,
                        :min_lat,
                        :res_lon,
                        :res_lat
                        ) AS grid_geom,
        COUNT(*) AS point_count
    FROM
        (SELECT modelresult.realization_id, seismicevent.coordinates
            FROM modelresult
                JOIN seismicevent
                    ON modelresult.oid = seismicevent.modelresult_oid
            WHERE modelresult.modelrun_oid = :modelrun_oid
        ) as events
    WHERE
      ST_X(events.coordinates)
        BETWEEN :min_lon AND :max_lon
      AND ST_Y(events.coordinates)
        BETWEEN :min_lat AND :max_lat
    GROUP BY grid_geom
)
SELECT
    ST_X(grid_geom) AS grid_lon,
    ST_Y(grid_geom) AS grid_lat,
    point_count
FROM grid_cells;
"""

router = APIRouter(tags=['modelruns'])


@router.get("/modelruns/{modelrun_id}/eventcounts",
            response_model=ModelRunRateGridSchema,
            response_model_exclude_none=True)
async def get_modelrun_rates(db: DBSessionDep,
                             modelrun_id: UUID,
                             min_lon: float,
                             min_lat: float,
                             res_lon: float,
                             res_lat: float,
                             max_lon: float,
                             max_lat: float,
                             realization_id: bool = False
                             ):

    # Execute the query
    stmt = text(QUERY1).bindparams(modelrun_oid=modelrun_id,
                                   min_lon=min_lon + (res_lon / 2),
                                   min_lat=min_lat + (res_lat / 2),
                                   max_lon=max_lon,
                                   max_lat=max_lat,
                                   res_lon=res_lon,
                                   res_lat=res_lat)
    result = await db.execute(stmt)
    rows = result.fetchall()  # Fetch all results
    columns = result.keys()   # Get column names

    # Convert to Pandas DataFrame
    df = pd.DataFrame(rows, columns=columns)
    df['grid_lat'] = np.round(df['grid_lat'], 6)
    df['grid_lon'] = np.round(df['grid_lon'], 6)

    # make sure that all the lon and lat values are at least
    # once in the df so that the grid is complete
    bg_lons = np.round(np.arange(min_lon + (res_lon / 2),
                       max_lon, res_lon), 6)
    bg_lats = np.round(np.arange(min_lat + (res_lat / 2),
                       max_lat, res_lat), 6)

    missing_lon = list(set(bg_lons) - set(df['grid_lon']))
    missing_lat = list(set(bg_lats) - set(df['grid_lat']))

    fillvalue = min(missing_lon, missing_lat, key=len)[-1]
    zipped = list(itertools.zip_longest(
        missing_lon, missing_lat, fillvalue=fillvalue))

    df = pd.concat([df, pd.DataFrame(
        [{'grid_lon': lon, 'grid_lat': lat, 'count': 0}
         for lon, lat in zipped])], ignore_index=True)

    # return a csv
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)

    csv_content = csv_buffer.getvalue()
    return Response(content=csv_content, media_type="text")
