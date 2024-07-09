from datetime import datetime
from uuid import UUID, uuid4

from hermes.datamodel import EStatus
from hermes.schemas.base import CreationInfoMixin


class ForecastSeries(CreationInfoMixin):
    oid: UUID = uuid4()
    project_oid: UUID
    name: str

    active: bool = True
    status: EStatus = EStatus.PENDING

    forecast_starttime: datetime
    forecast_endtime: datetime | None = None
    forecast_interval: int | None = None
    forecast_duration: int | None = None

    observation_starttime: datetime | None = None
    observation_endtime: datetime | None = None

    bounding_polygon: str | None = None
    altitude_min: float | None = None
    altitude_max: float | None = None
