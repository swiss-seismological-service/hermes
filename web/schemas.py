import json
from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator
from typing_extensions import Self

from hermes.repositories.types import PolygonType, db_to_shapely
from hermes.schemas import Forecast, ForecastSeries, Project
from hermes.schemas.base import EResultType, Model
from web.mixins import CreationInfoMixin


class ProjectJSON(CreationInfoMixin, Project):
    pass


class ModelConfigNameSchema(Model):
    name: str | None
    oid: UUID


class InjectionPlanNameSchema(Model):
    name: str | None
    oid: UUID


class ForecastSeriesJSON(CreationInfoMixin, ForecastSeries):
    modelconfigs: list[ModelConfigNameSchema] | None = None
    injectionplans: list[InjectionPlanNameSchema] | None
    bounding_polygon: str | PolygonType | None = None

    @field_validator('bounding_polygon', mode='after')
    @classmethod
    def validate_bounding_polygon(cls, value: PolygonType) -> Self:
        return db_to_shapely(value).wkt


class ForecastJSON(CreationInfoMixin, Forecast):
    pass


class InjectionPlanJSON(InjectionPlanNameSchema):
    borehole_hydraulics: dict | None = Field(validation_alias="template")

    @field_validator('borehole_hydraulics', mode='before')
    @classmethod
    def load_data(cls, v: str) -> dict:
        return json.loads(v)


class ModelResultJSON(Model):
    gridcell_oid: UUID | None = None
    timestep_oid: UUID | None = None
    result_type: EResultType | None = None
    starttime: datetime | None = None
    endtime: datetime | None = None
    geom: str | PolygonType | None = None
    depth_min: float | None = None
    depth_max: float | None = None
    result_id: int | None = None

    @field_validator('geom', mode='after')
    @classmethod
    def validate_geom(cls, value: PolygonType) -> Self:
        return db_to_shapely(value).wkt

    model_config = ConfigDict(
        **Model.model_config,
        ser_exclude={"gridcell_oid", "timestep_oid"}
    )
