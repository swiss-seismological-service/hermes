import json
from datetime import datetime
from uuid import UUID

from pydantic import Field, computed_field, field_validator, model_validator
from typing_extensions import Self

from hermes.repositories.types import PolygonType, db_to_shapely
from hermes.schemas import Forecast, ForecastSeries, ModelRun, Project
from hermes.schemas.base import Model
from hermes.schemas.result_schemas import GridCell, TimeStep
from web.mixins import (CreationInfoMixin, RealFloatValueSchema,
                        real_float_value_mixin)


class ProjectSchema(CreationInfoMixin, Project):
    pass


class ModelConfigNameSchema(Model):
    name: str | None
    oid: UUID


class InjectionPlanNameSchema(Model):
    name: str | None
    oid: UUID


class ForecastSeriesSchema(CreationInfoMixin, ForecastSeries):
    modelconfigs: list[ModelConfigNameSchema] | None = None
    injectionplans: list[InjectionPlanNameSchema] | None
    bounding_polygon: str | PolygonType | None = None

    @field_validator('bounding_polygon', mode='after')
    @classmethod
    def validate_bounding_polygon(cls, value: PolygonType) -> Self:
        return db_to_shapely(value).wkt


class ForecastSchema(CreationInfoMixin, Forecast):
    pass


class ModelRunDetailSchema(ModelRun):
    forecast_oid: UUID = Field(exclude=True)
    modelconfig: ModelConfigNameSchema | None = \
        Field(default=None, exclude=True)
    injectionplan: InjectionPlanNameSchema | None = \
        Field(default=None, exclude=True)

    @computed_field
    @property
    def modelconfig_name(self) -> str:
        return self.modelconfig.name

    @computed_field
    @property
    def injectionplan_name(self) -> str:
        return self.injectionplan.name


class ForecastDetailSchema(ForecastSchema):
    modelruns: list[ModelRunDetailSchema] | None = None


class InjectionPlanSchema(InjectionPlanNameSchema):
    borehole_hydraulics: dict | None = Field(validation_alias="data")

    @field_validator('borehole_hydraulics', mode='before')
    @classmethod
    def load_data(cls, v: str) -> dict:
        return json.loads(v)


class ForecastRateSchema(real_float_value_mixin('b', float),
                         real_float_value_mixin('number_events', float),
                         real_float_value_mixin('a', float),
                         real_float_value_mixin('alpha', float),
                         real_float_value_mixin('mc', float)):
    pass


class ResultBinSchema(Model):

    a: RealFloatValueSchema | None = None
    b: RealFloatValueSchema | None = None
    number_events: RealFloatValueSchema | None = None
    alpha: RealFloatValueSchema | None = None
    mc: RealFloatValueSchema | None = None
    realization_id: int | None = None

    timestep: TimeStep = Field(exclude=True)
    gridcell: GridCell = Field(exclude=True)

    @model_validator(mode='before')
    def hoist_params(cls, data):
        try:
            grparams = ForecastRateSchema.model_validate(
                data.grparameters[0])

            for key in ('a', 'b', 'number_events', 'alpha', 'mc'):
                setattr(data, key, getattr(grparams, key))
            return data

        except BaseException:
            return data

    @computed_field
    @property
    def starttime(self) -> datetime:
        return self.timestep.starttime

    @computed_field
    @property
    def endtime(self) -> datetime:
        return self.timestep.endtime

    @computed_field
    @property
    def depth_min(self) -> float:
        return self.gridcell.depth_min

    @computed_field
    @property
    def depth_max(self) -> float:
        return self.gridcell.depth_max

    @computed_field
    @property
    def latitude_min(self) -> float:
        return self.gridcell.geom.bounds[1]

    @computed_field
    @property
    def latitude_max(self) -> float:
        return self.gridcell.geom.bounds[3]

    @computed_field
    @property
    def longitude_min(self) -> float:
        return self.gridcell.geom.bounds[0]

    @computed_field
    @property
    def longitude_max(self) -> float:
        return self.gridcell.geom.bounds[2]


class ModelRunRateGridSchema(ModelRunDetailSchema):
    rateforecasts: list[ResultBinSchema] | None = Field(
        validation_alias="modelresults")
