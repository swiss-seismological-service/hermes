import enum

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        arbitrary_types_allowed=True,
        from_attributes=True)


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
