
import json
from uuid import UUID

from pydantic import Field, computed_field, field_validator
from typing_extensions import Self

from hermes.repositories.types import PolygonType, db_to_shapely
from hermes.schemas import Forecast, ForecastSeries, ModelRun, Project
from hermes.schemas.base import Model
from web.mixins import CreationInfoMixin


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
