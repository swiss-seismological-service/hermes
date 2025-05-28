import json
from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field, computed_field, field_validator
from typing_extensions import Self

from hermes.repositories.types import PolygonType, db_to_shapely
from hermes.schemas import ForecastSeries, Project
from hermes.schemas.base import EResultType, EStatus, Model


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


class ModelConfigNameSchema(Model):
    oid: UUID
    name: str
    result_type: EResultType | None = None


class InjectionPlanNameSchema(Model):
    oid: UUID
    name: str


class SeismicityObservationOIDSchema(Model):
    oid: UUID


class InjectionObservationOIDSchema(Model):
    oid: UUID


class ModelRunJSON(Model):
    oid: UUID
    modelconfig: ModelConfigNameSchema | None = None
    injectionplan: InjectionPlanNameSchema | None = None
    status: EStatus | None = None


class ForecastJSON(CreationInfoMixin):
    oid: UUID

    status: EStatus

    starttime: datetime | None = None
    endtime: datetime | None = None

    forecastseries_oid: UUID = Field(exclude=True)
    seismicityobservation: SeismicityObservationOIDSchema | None = None
    injectionobservation: InjectionObservationOIDSchema | None = None

    modelruns: list[ModelRunJSON] = []


class ForecastSeriesJSON(CreationInfoMixin, ForecastSeries):
    modelconfigs: list[ModelConfigNameSchema] | None = None
    injectionplans: list[InjectionPlanNameSchema] | None
    bounding_polygon: str | PolygonType | None = None

    @field_validator('bounding_polygon', mode='after')
    @classmethod
    def validate_bounding_polygon(cls, value: PolygonType) -> Self:
        return db_to_shapely(value).wkt


class ProjectJSON(CreationInfoMixin, Project):
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
    result_type: EResultType
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


class ModelRunJSON(Model):
    oid: UUID
    modelconfig: ModelConfigNameSchema | None = None
    injectionplan: InjectionPlanNameSchema | None = None
    status: EStatus | None = None
    results: list[ModelResultJSON] = []
