from uuid import UUID

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
