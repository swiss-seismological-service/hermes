from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import ConfigDict, field_validator
from shapely import Polygon

from hermes.schemas.base import Model
from hermes.schemas.project_schemas import ModelConfig


class ModelInput(Model):
    forecast_start: datetime
    forecast_end: datetime
    injection_observation: list[dict] | None = None
    injection_plan: dict | None = None
    seismicity_observation: str | None = None
    bounding_polygon: Polygon | None = None
    depth_min: float | None = None
    depth_max: float | None = None
    config: dict | None = None

    model_config = ConfigDict(
        protected_namespaces=()
    )


class ModelRunInfo(Model):
    forecast_oid: UUID | None = None
    forecast_start: datetime | None = None
    forecast_end: datetime | None = None

    injection_observation_oid: UUID | None = None
    injection_plan_oid: UUID | None = None
    seismicity_observation_oid: UUID | None = None

    bounding_polygon: str | None = None
    depth_min: float | None = None
    depth_max: float | None = None

    config: ModelConfig

    @field_validator('bounding_polygon', mode='before')
    @classmethod
    def validate_bounding_polygon(cls, value: Any):
        if isinstance(value, Polygon):
            return value.wkt
        return value
