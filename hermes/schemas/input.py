from uuid import UUID

from hermes.schemas.base import Model


class SeismicityObservation(Model):
    oid: UUID | None = None
    data: str | None = None


class InjectionObservation(Model):
    oid: UUID | None = None
    data: str | None = None


class InjectionPlan(Model):
    oid: UUID | None = None
    data: str | None = None
