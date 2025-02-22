-- given a modelrun_oid, return the number of seismic events in each grid cell
-- while preserving the realization_id of the events
WITH grid_cells AS (
	SELECT ST_SnapToGrid(events.coordinates, 0.05, 0.05) AS grid_geom,
		events.realization_id as realization_id,
		COUNT(*) AS point_count
		FROM
		(SELECT modelresult.realization_id, seismicevent.coordinates
			FROM modelresult 
				JOIN seismicevent 
					ON modelresult.oid = seismicevent.modelresult_oid
			WHERE modelresult.modelrun_oid = '16fb18c6-1d9a-4c0b-bc09-9f5b04c0b5f3'
		) as events
	WHERE
		ST_X(events.coordinates) BETWEEN 5.781534575286801 AND 10.622251067093229
		AND ST_Y(events.coordinates) BETWEEN 45.67566844294226 AND 47.98038803257793
	GROUP BY grid_geom, realization_id
)
SELECT 
    ST_X(grid_geom) AS grid_lon,
    ST_Y(grid_geom) AS grid_lat,
    point_count,
	realization_id
FROM grid_cells;

-- same thing without preserving realization_id
WITH grid_cells AS (
	SELECT ST_SnapToGrid(events.coordinates, 0.05, 0.05) AS grid_geom,
		COUNT(*) AS point_count
		FROM
		(SELECT modelresult.realization_id, seismicevent.coordinates
			FROM modelresult 
				JOIN seismicevent 
					ON modelresult.oid = seismicevent.modelresult_oid
			WHERE modelresult.modelrun_oid = '16fb18c6-1d9a-4c0b-bc09-9f5b04c0b5f3'
		) as events
	WHERE
		ST_X(events.coordinates) BETWEEN 5.781534575286801 AND 10.622251067093229
		AND ST_Y(events.coordinates) BETWEEN 45.67566844294226 AND 47.98038803257793
	GROUP BY grid_geom
)
SELECT 
    ST_X(grid_geom) AS grid_lon,
    ST_Y(grid_geom) AS grid_lat,
    point_count
FROM grid_cells;

-- count events per realization inside a bounding box
SELECT 
	events.realization_id as realization_id,
	COUNT(*) AS point_count
FROM
	(SELECT modelresult.realization_id, seismicevent.coordinates
		FROM modelresult 
			JOIN seismicevent 
				ON modelresult.oid = seismicevent.modelresult_oid
		WHERE modelresult.modelrun_oid = '16fb18c6-1d9a-4c0b-bc09-9f5b04c0b5f3'
	) as events
WHERE
	ST_X(events.coordinates) BETWEEN 5.781534575286801 AND 10.622251067093229
	AND ST_Y(events.coordinates) BETWEEN 45.67566844294226 AND 47.98038803257793
GROUP BY realization_id;

-- for one forecastseries and modelconfig, count events per modelrun and realization inside a bounding box
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
	WHERE forecast.forecastseries_oid = '2bce8065-489d-4103-8e76-4b960d4b8d84'
	AND modelrun.modelconfig_oid = 'd063c323-2ad0-44f6-afc6-723f5532e7ff'
	) as events
WHERE
	ST_X(events.coordinates) BETWEEN 5.781534575286801 AND 10.622251067093229
	AND ST_Y(events.coordinates) BETWEEN 45.67566844294226 AND 47.98038803257793
GROUP BY realization_id, modelrun_oid, forecast_oid