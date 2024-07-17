

from typing import Callable, Generic, TypeVar

from pydantic import Field, computed_field, create_model

from hermes.schemas.base import Model

DataT = TypeVar('DataT')


class RealValueSchema(Model, Generic[DataT]):
    value: DataT | None = None
    uncertainty: float | None = None
    loweruncertainty: float | None = None
    upperuncertainty: float | None = None
    confidencelevel: float | None = None


def real_value_factory(name: str, real_type: TypeVar) -> Callable:
    def create_schema(obj: Model) -> RealValueSchema[real_type]:
        return RealValueSchema[real_type](
            value=getattr(obj, f'{name}_value'),
            uncertainty=getattr(obj, f'{name}_uncertainty'),
            loweruncertainty=getattr(obj, f'{name}_loweruncertainty'),
            upperuncertainty=getattr(obj, f'{name}_upperuncertainty'),
            confidencelevel=getattr(obj, f'{name}_confidencelevel'))
    return create_schema


def real_value_mixin(field_name: str, real_type: TypeVar) -> Model:
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
         computed_field(real_value_factory(field_name, real_type)))
    ])

    retval = create_model(field_name, __base__=Model, **_func_map)

    return retval
