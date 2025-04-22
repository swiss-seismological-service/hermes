import json
from uuid import UUID

from pydantic import Field, field_validator
from typing_extensions import Self

from hermes.repositories.types import PolygonType, db_to_shapely
from hermes.schemas import Forecast, ForecastSeries, Project
from hermes.schemas.base import Model
from web.mixins import CreationInfoMixin


class ProjectJSONSchema(CreationInfoMixin, Project):
    pass


class ModelConfigNameSchema(Model):
    name: str | None
    oid: UUID


class InjectionPlanNameSchema(Model):
    name: str | None
    oid: UUID


class ForecastSeriesJSONSchema(CreationInfoMixin, ForecastSeries):
    modelconfigs: list[ModelConfigNameSchema] | None = None
    injectionplans: list[InjectionPlanNameSchema] | None
    bounding_polygon: str | PolygonType | None = None

    @field_validator('bounding_polygon', mode='after')
    @classmethod
    def validate_bounding_polygon(cls, value: PolygonType) -> Self:
        return db_to_shapely(value).wkt


class ForecastSchema(CreationInfoMixin, Forecast):
    pass


class InjectionPlanSchema(InjectionPlanNameSchema):
    borehole_hydraulics: dict | None = Field(validation_alias="template")

    @field_validator('borehole_hydraulics', mode='before')
    @classmethod
    def load_data(cls, v: str) -> dict:
        return json.loads(v)
