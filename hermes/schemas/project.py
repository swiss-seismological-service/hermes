from datetime import datetime
from uuid import UUID

from hermes.schemas.base import EInput
from hermes.schemas.mixins import CreationInfoMixin


class Project(CreationInfoMixin):
    oid: UUID | None = None
    name: str | None = None
    starttime: datetime | None = None
    endtime: datetime | None = None

    seismicityobservation_required: EInput = EInput.REQUIRED
    injectionobservation_required: EInput = EInput.REQUIRED
    injectionplan_required: EInput = EInput.REQUIRED

    description: str | None = None
    fdsnws_url: str | None = None
    hydws_url: str | None = None
