from datetime import datetime, timezone
from typing import TypeVar

from pydantic import Field, create_model

from hermes.schemas.base import Model


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
