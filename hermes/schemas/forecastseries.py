from datetime import datetime
from uuid import UUID

from hermes.datamodel import EStatus
from hermes.schemas.base import CreationInfoMixin


class ForecastSeries(CreationInfoMixin):
    oid: UUID | None = None
    project_oid: UUID | None = None
    name: str | None = None

    active: bool = True
    status: EStatus = EStatus.PENDING

    forecast_starttime: datetime | None = None
    forecast_endtime: datetime | None = None
    forecast_interval: int | None = None
    forecast_duration: int | None = None

    observation_starttime: datetime | None = None
    observation_endtime: datetime | None = None

    bounding_polygon: str | None = None
    altitude_min: float | None = None
    altitude_max: float | None = None

    tags: list[str] = []
