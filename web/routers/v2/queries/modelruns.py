EVENTCOUNTS = """
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
