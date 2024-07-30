import json
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator
from shapely import Polygon

from hermes.repositories.types import PolygonType, polygon_converter
from hermes.schemas.base import (CreationInfoMixin, EInput, EResultType,
                                 EStatus, Model)
from hermes.utils.geometry import convert_input_to_polygon


class Project(CreationInfoMixin):
    oid: UUID | None = None
    name: str | None = None
    starttime: datetime | None = None
    endtime: datetime | None = None

    seismicityobservation_required: EInput = EInput.REQUIRED
    injectionobservation_required: EInput = EInput.REQUIRED
    injectionplan_required: EInput = EInput.REQUIRED

    description: str | None = None
    fdsnws_url: str | None = None
    hydws_url: str | None = None


class ForecastSeries(CreationInfoMixin):
    oid: UUID | None = None
    project_oid: UUID | None = None
    name: str | None = None
    description: str | None = None
    status: EStatus | None = None

    forecast_starttime: datetime | None = None
    forecast_endtime: datetime | None = None
    forecast_interval: int | None = None
    forecast_duration: int | None = None

    observation_starttime: datetime | None = None
    observation_endtime: datetime | None = None

    bounding_polygon: Polygon | None = None
    depth_min: float | None = None
    depth_max: float | None = None

    injection_plan: dict | None = Field(None, exclude=True)

    tags: list[str] = []

    @field_validator('bounding_polygon', mode='before')
    @classmethod
    def validate_bounding_polygon(cls, value: Any):
        if isinstance(value, dict):
            value = json.dumps(value)

        if isinstance(value, PolygonType):
            return polygon_converter(value)

        if isinstance(value, str):
            return convert_input_to_polygon(value)

        return value


class Forecast(CreationInfoMixin):
    oid: UUID | None = None
    name: str | None = None

    status: EStatus | None = None

    starttime: datetime | None = None
    endtime: datetime | None = None

    forecastseries_oid: UUID | None = None

    seismicity_observation: str | None = Field(None, exclude=True)
    injection_observation: list[dict] | None = Field(None, exclude=True)


class ModelConfig(Model):
    oid: UUID | None = None
    name: str | None = None
    enabled: bool = True
    description: str | None = None
    result_type: EResultType | None = None
    sfm_module: str | None = None
    sfm_function: str | None = None
    last_modified: datetime | None = None

    config: dict = {}

    tags: list[str] = []


class Tag(Model):
    oid: UUID | None = None
    name: str | None = None
