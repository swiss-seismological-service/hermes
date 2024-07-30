from datetime import datetime

from pydantic import ConfigDict
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
    config: ModelConfig
    input: ModelInput
