import enum
from datetime import datetime, timezone
from typing import TypeVar

from pydantic import (BaseModel, BeforeValidator, ConfigDict, Field,
                      create_model)
from typing_extensions import Annotated


class Model(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        arbitrary_types_allowed=True,
        from_attributes=True,
        protected_namespaces=())


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


class CreationInfoMixin(Model):
    creationinfo_author: str | None = None
    creationinfo_agencyid: str | None = None
    creationinfo_creationtime: datetime = datetime.now(
        timezone.utc).replace(microsecond=0)
    creationinfo_version: str | None = None


def real_value_mixin(field_name: str, real_type: TypeVar) -> Model:
    _func_map = dict([
        (f'{field_name}_value',
         (real_type | None, Field(default=None))),
        (f'{field_name}_uncertainty',
         (float | None, Field(default=None))),
        (f'{field_name}_loweruncertainty',
         (float | None, Field(default=None))),
        (f'{field_name}_upperuncertainty',
         (float | None, Field(default=None))),
        (f'{field_name}_confidencelevel',
         (float | None, Field(default=None))),
    ])

    retval = create_model(field_name, __base__=Model, **_func_map)

    return retval


def sd_validator(val):
    if isinstance(val, datetime):
        return val.strftime('%Y-%m-%dT%H:%M:%S')
    elif isinstance(val, str):
        try:
            datetime.strptime(val, '%Y-%m-%dT%H:%M:%S')
            return val
        except Exception:
            raise ValueError('Invalid datetime string.')
    else:
        raise ValueError('Invalid datetime format. Please '
                         'provide a datetime object or a string '
                         'in the format %Y-%m-%dT%H:%M:%S.')


DatetimeString = Annotated[
    str,
    BeforeValidator(sd_validator),
    'Datetime string in the format %Y-%m-%dT%H:%M:%S or a datetime object.'
]
