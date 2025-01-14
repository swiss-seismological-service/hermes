from uuid import UUID

from shapely import Point

from hermes.schemas.base import Model, real_value_mixin


class SeismicityObservation(Model):
    oid: UUID | None = None
    data: bytes | None = None
    forecast_oid: UUID | None = None


class InjectionPlanTemplate(Model):
    type: str | None = None
    section_name: str | None = None
    borehole_name: str | None = None
    resolution: int | None = None
    config: dict | None = None


class InjectionObservation(Model):
    oid: UUID | None = None
    data: bytes | None = None
    forecast_oid: UUID | None = None


class InjectionPlan(Model):
    oid: UUID | None = None
    data: bytes | None = None
    template: bytes | None = None
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
    associatedphasecount: int | None = None
    usedphasecount: int | None = None
    associatedstationcount: int | None = None
    usedstationcount: int | None = None
    coordinates: Point | None = None
