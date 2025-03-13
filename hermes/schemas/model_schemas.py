from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import field_validator
from shapely import Polygon

from hermes.schemas.base import EResultType, Model


class ModelConfig(Model):
    oid: UUID | None = None
    name: str | None = None
    enabled: bool = True
    description: str | None = None
    result_type: EResultType | None = None
    sfm_module: str | None = None
    sfm_function: str | None = None
    last_modified: datetime | None = None

    model_parameters: dict = {}

    tags: list[str] = []


class BaseModelRunInfo(Model):
    """
    Base Information for a model run.
    """

    forecast_start: datetime | None = None
    forecast_end: datetime | None = None

    bounding_polygon: str | None = None
    depth_min: float | None = None
    depth_max: float | None = None

    model_settings: dict = {}

    @field_validator('bounding_polygon', mode='before')
    @classmethod
    def validate_bounding_polygon(cls, value: Any):
        if isinstance(value, Polygon):
            return value.wkt
        return value


class DBModelRunInfo(BaseModelRunInfo):
    """
    Information for a model run, retrieving and storing
    data directly to/from the database.
    """

    forecast_oid: UUID | None = None
    forecastseries_oid: UUID | None = None
    injection_observation_oid: UUID | None = None
    injection_plan_oid: UUID | None = None
    seismicity_observation_oid: UUID | None = None
