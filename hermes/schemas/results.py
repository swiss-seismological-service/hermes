from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import field_validator
from shapely import Polygon

from hermes.repositories.shapes import PolygonType, polygon_converter
from hermes.schemas.base import EResultType, Model


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


class SeismicEvent(Model):
    pass
