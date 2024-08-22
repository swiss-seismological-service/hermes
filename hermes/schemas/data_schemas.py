from uuid import UUID

from shapely import Point

from hermes.schemas.base import Model


class SeismicityObservation(Model):
    oid: UUID | None = None
    data: bytes | None = None
    forecast_oid: UUID | None = None


class InjectionObservation(Model):
    oid: UUID | None = None
    data: bytes | None = None
    forecast_oid: UUID | None = None


class InjectionPlan(Model):
    oid: UUID | None = None
    data: bytes | None = None
    forecastseries_oid: UUID | None = None


class EventObservation(Model):
    oid: UUID | None = None
    time: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    depth: float | None = None
    magnitude: float | None = None
    magnitude_type: str | None = None
    associated_phasecount: int | None = None
    seismicityobservation_oid: UUID | None = None
    coordinates: Point | None = None
