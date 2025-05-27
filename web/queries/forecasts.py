OBSERVED_EVENTS = """
SELECT eventobservation.*
FROM eventobservation
JOIN seismicityobservation
    ON eventobservation.seismicityobservation_oid = seismicityobservation.oid
WHERE seismicityobservation.forecast_oid = :forecast_id
AND eventobservation.time_value >= :start_time
AND eventobservation.time_value <= :end_time
AND eventobservation.magnitude_value >= :min_mag
AND ST_Within(
    eventobservation.coordinates,
    ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)
);
"""
