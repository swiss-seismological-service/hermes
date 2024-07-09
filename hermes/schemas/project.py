from datetime import datetime
from uuid import UUID, uuid4

from hermes.datamodel.project import EInput
from hermes.schemas.base import CreationInfoMixin


class Project(CreationInfoMixin):
    oid: UUID = uuid4()
    name: str
    starttime: datetime

    seismiccatalog_required: EInput = EInput.REQUIRED
    injectionwell_required: EInput = EInput.REQUIRED
    injectionplan_required: EInput = EInput.REQUIRED

    description: str | None = None
    endtime: datetime | None = None
    fdsnws_url: str | None = None
    hydws_url: str | None = None
