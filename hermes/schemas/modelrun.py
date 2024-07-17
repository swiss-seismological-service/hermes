from uuid import UUID

from hermes.schemas.base import EStatus, Model


class ModelRun(Model):
    oid: UUID | None = None
    status: EStatus | None = None

    modelconfig_oid: UUID | None = None
    forecast_oid: UUID | None = None
    injectionplan_oid: UUID | None = None
