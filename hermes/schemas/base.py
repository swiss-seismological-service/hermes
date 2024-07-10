import enum
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    model_config = ConfigDict(extra='allow',
                              arbitrary_types_allowed=True,
                              from_attributes=True)


class CreationInfoMixin(Model):
    creationinfo_author: str | None = None
    creationinfo_agencyid: str | None = None
    creationinfo_creationtime: datetime = datetime.now(
        timezone.utc).replace(microsecond=0)
    creationinfo_version: str | None = None


class EInput(str, enum.Enum):
    REQUIRED = 'REQUIRED'
    OPTIONAL = 'OPTIONAL'
    NOT_ALLOWED = 'NOT_ALLOWED'


class EStatus(str, enum.Enum):
    PENDING = 'PENDING'
    SCHEDULED = 'SCHEDULED'
    PAUSED = 'PAUSED'
    RUNNING = 'RUNNING'
    CANCELLED = 'CANCELLED'
    FAILED = 'FAILED'
    COMPLETED = 'COMPLETED'


class EResultType(str, enum.Enum):
    GRID = 'GRID'
    CATALOG = 'CATALOG'
    BINS = 'BINS'
