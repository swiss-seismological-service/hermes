EVENTCOUNTS = """
WITH grid_cells AS (
    SELECT ST_SnapToGrid(events.coordinates,
                        :min_lon,
                        :min_lat,
                        :res_lon,
                        :res_lat
                        ) AS grid_geom,
        COUNT(*) AS event_count
    FROM
        (SELECT modelresult.realization_id, eventforecast.coordinates
            FROM modelresult
                JOIN eventforecast
                    ON modelresult.oid = eventforecast.modelresult_oid
            WHERE modelresult.modelrun_oid = :modelrun_oid
        ) as events
    WHERE ST_Within(
            events.coordinates,
            ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))
    GROUP BY grid_geom
)
SELECT
    ST_X(grid_geom) AS grid_lon,
    ST_Y(grid_geom) AS grid_lat,
    event_count
FROM grid_cells;
"""
