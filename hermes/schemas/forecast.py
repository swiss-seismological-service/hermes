from datetime import datetime
from uuid import UUID

from hermes.schemas.base import CreationInfoMixin, EStatus


class Forecast(CreationInfoMixin):
    oid: UUID | None = None
    name: str | None = None

    status: EStatus = EStatus.PENDING

    starttime: datetime | None = None
    endtime: datetime | None = None

    forecastseries_oid: UUID | None = None
    seismicityobservation_oid: UUID | None = None
    injectionobservation_oid: UUID | None = None
