from datetime import datetime
from uuid import UUID, uuid4

from hermes.datamodel import EStatus
from hermes.schemas.base import CreationInfoMixin


class ForecastSeries(CreationInfoMixin):
    oid: UUID = uuid4()
    project_oid: UUID

    name: str | None = None
    active: bool = True
    status: EStatus = EStatus.PENDING

    starttime: datetime | None = None
    endtime: datetime | None = None

    forecastinterval: int | None = None
    forecastduration: int | None = None
    boundingpolygon: str | None = None
    altitudemin: float | None = None
    altitudemax: float | None = None
