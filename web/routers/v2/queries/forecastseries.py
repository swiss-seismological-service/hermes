# for one forecastseries and modelconfig, count events per
# modelrun and realization inside a bounding box
EVENT_COUNT_SERIES = """
SELECT
    forecast_oid,
    modelrun_oid,
    realization_id,
    COUNT(*) AS point_count
FROM (
    SELECT
    forecast.oid as forecast_oid,
        modelrun.oid as modelrun_oid,
        modelresult.realization_id as realization_id,
        seismicevent.coordinates as coordinates
    FROM forecast
    JOIN modelrun
        ON forecast.oid = modelrun.forecast_oid
    JOIN modelresult
        ON modelrun.oid = modelresult.modelrun_oid
    JOIN seismicevent
        ON modelresult.oid = seismicevent.modelresult_oid
    WHERE forecast.forecastseries_oid = :forecastseries_oid
    AND modelrun.modelconfig_oid = :modelconfig_oid
    ) as events
WHERE
    ST_X(events.coordinates) BETWEEN :min_lon AND :max_lon
    AND ST_Y(events.coordinates) BETWEEN :min_lat AND :max_lat
GROUP BY realization_id, modelrun_oid, forecast_oid
"""
