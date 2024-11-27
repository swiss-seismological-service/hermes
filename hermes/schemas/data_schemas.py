from uuid import UUID

from shapely import Point

from hermes.schemas.base import Model, real_value_mixin


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
    name: str | None = None
    forecastseries_oid: UUID | None = None


class EventObservation(real_value_mixin('time', float),
                       real_value_mixin('latitude', float),
                       real_value_mixin('longitude', float),
                       real_value_mixin('depth', float),
                       real_value_mixin('magnitude', float)
                       ):
    oid: UUID | None = None
    magnitude_type: str | None = None
    event_type: str | None = None
    seismicityobservation_oid: UUID | None = None
    associated_phasecount: int | None = None
    used_phasecount: int | None = None
    coordinates: Point | None = None
