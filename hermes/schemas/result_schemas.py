from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import field_validator
from shapely import Polygon

from hermes.repositories.types import PolygonType, polygon_converter
from hermes.schemas.base import EResultType, EStatus, Model, real_value_mixin


class ModelRun(Model):
    oid: UUID | None = None
    status: EStatus | None = None

    modelconfig_oid: UUID | None = None
    forecast_oid: UUID | None = None
    injectionplan_oid: UUID | None = None


class ModelResult(Model):
    oid: UUID | None = None
    result_type: EResultType | None = None
    timestep_oid: UUID | None = None
    gridcell_oid: UUID | None = None
    modelrun_oid: UUID | None = None


class TimeStep(Model):
    oid: UUID | None = None
    starttime: datetime | None = None
    endtime: datetime | None = None
    forecastseries_oid: UUID | None = None


class GridCell(Model):
    oid: UUID | None = None
    geom: Polygon | None = None
    depth_min: float | None = None
    depth_max: float | None = None
    forecastseries_oid: UUID | None = None

    @field_validator('geom', mode='before')
    @classmethod
    def validate_geom(cls, value: Any):
        if isinstance(value, PolygonType):
            return polygon_converter(value)
        return value


class SeismicEvent(real_value_mixin('longitude', float),
                   real_value_mixin('latitude', float),
                   real_value_mixin('depth', float),
                   real_value_mixin('magnitude', float),
                   real_value_mixin('time', datetime)
                   ):
    oid: UUID | None = None
    magnitude_type: str | None = None
    modelresult_oid: UUID | None = None
