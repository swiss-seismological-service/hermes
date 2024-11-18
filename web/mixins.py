from typing import Callable, Generic, TypeVar
from datetime import datetime

from pydantic import Field, computed_field, create_model

from hermes.schemas.base import Model


class CreationInfoSchema(Model):
    author: str | None = None
    agencyid: str | None = None
    creationtime: datetime | None = None
    version: str | None = None
    copyrightowner: str | None = None
    licence: str | None = None


def creationinfo_factory(obj: Model) -> CreationInfoSchema:
    return CreationInfoSchema(
        author=obj.creationinfo_author,
        agencyid=obj.creationinfo_agencyid,
        creationtime=obj.creationinfo_creationtime,
        version=obj.creationinfo_version,
        copyrightowner=obj.creationinfo_copyrightowner,
        licence=obj.creationinfo_licence)


class CreationInfoMixin(Model):
    creationinfo_author: str | None = Field(default=None, exclude=True)
    creationinfo_agencyid: str | None = Field(default=None, exclude=True)
    creationinfo_creationtime: datetime = Field(default=None, exclude=True)
    creationinfo_version: str | None = Field(default=None, exclude=True)
    creationinfo_copyrightowner: str | None = Field(default=None, exclude=True)
    creationinfo_licence: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def creationinfo(self) -> CreationInfoSchema:
        return creationinfo_factory(self)


DataT = TypeVar('DataT')


class RealFloatValueSchema(Model, Generic[DataT]):
    value: DataT | None = None
    uncertainty: float | None = None
    loweruncertainty: float | None = None
    upperuncertainty: float | None = None
    confidencelevel: float | None = None


def real_float_value_factory(name: str, real_type: TypeVar) -> Callable:
    def create_schema(obj: Model) -> RealFloatValueSchema[TypeVar]:
        return RealFloatValueSchema[real_type](
            value=getattr(
                obj, f'{name}_value'), uncertainty=getattr(
                obj, f'{name}_uncertainty'), loweruncertainty=getattr(
                obj, f'{name}_loweruncertainty'), upperuncertainty=getattr(
                    obj, f'{name}_upperuncertainty'), confidencelevel=getattr(
                        obj, f'{name}_confidencelevel'))
    return create_schema


def real_float_value_mixin(field_name: str, real_type: TypeVar) -> Model:
    _func_map = dict([
        (f'{field_name}_value',
         (real_type | None, Field(default=None, exclude=True))),
        (f'{field_name}_uncertainty',
         (float | None, Field(default=None, exclude=True))),
        (f'{field_name}_loweruncertainty',
         (float | None, Field(default=None, exclude=True))),
        (f'{field_name}_upperuncertainty',
         (float | None, Field(default=None, exclude=True))),
        (f'{field_name}_confidencelevel',
         (float | None, Field(default=None, exclude=True))),
        (field_name,
         computed_field(real_float_value_factory(field_name, real_type)))
    ])

    retval = create_model(field_name,
                          __base__=Model,
                          **_func_map)

    return retval
