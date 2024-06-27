from datetime import datetime, timezone
from uuid import UUID, uuid4

from hermes.datamodel.project import EInput
from hermes.schemas.base import CreationInfoMixin


class Project(CreationInfoMixin):
    oid: UUID = uuid4()
    starttime: datetime = datetime.now(timezone.utc)

    seismiccatalog_required: EInput = EInput.REQUIRED
    injectionwell_required: EInput = EInput.REQUIRED
    injectionplan_required: EInput = EInput.REQUIRED

    name: str | None = None
    endtime: datetime | None = None
    description: str | None = None
    seismiccatalog: str | None = None
    injectionwell: str | None = None
    fdsnws_url: str | None = None
    hydws_url: str | None = None
