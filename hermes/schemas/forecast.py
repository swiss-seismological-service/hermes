from datetime import datetime
from uuid import UUID

from hermes.schemas.base import EStatus
from hermes.schemas.mixins import CreationInfoMixin


class Forecast(CreationInfoMixin):
    oid: UUID | None = None
    name: str | None = None

    status: EStatus | None = None

    starttime: datetime | None = None
    endtime: datetime | None = None

    forecastseries_oid: UUID | None = None
    seismicityobservation_oid: UUID | None = None
    injectionobservation_oid: UUID | None = None
