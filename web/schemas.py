
from uuid import UUID

from pydantic import field_validator
from typing_extensions import Self

from hermes.repositories.types import PolygonType, db_to_shapely
from hermes.schemas import ForecastSeries, Project
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
