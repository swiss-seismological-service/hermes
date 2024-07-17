import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
from pydantic import field_validator
from shapely import Polygon, from_geojson, from_wkt

from hermes.repositories.shapes import PolygonType, polygon_converter
from hermes.schemas.base import CreationInfoMixin, EStatus


class ForecastSeries(CreationInfoMixin):
    oid: UUID | None = None
    project_oid: UUID | None = None
    name: str | None = None
    description: str | None = None
    status: EStatus = EStatus.PENDING

    forecast_starttime: datetime | None = None
    forecast_endtime: datetime | None = None
    forecast_interval: int | None = None
    forecast_duration: int | None = None

    observation_starttime: datetime | None = None
    observation_endtime: datetime | None = None

    bounding_polygon: Polygon | None = None
    depth_min: float | None = None
    depth_max: float | None = None

    tags: list[str] = []

    @field_validator('bounding_polygon', mode='before')
    @classmethod
    def validate_bounding_polygon(cls, value: Any):
        if isinstance(value, dict):
            value = json.dumps(value)

        if isinstance(value, PolygonType):
            return polygon_converter(value)

        if isinstance(value, str):
            if Path(value).exists():
                try:
                    if value.endswith('.npy'):
                        fl = np.load(value, mmap_mode='r')
                        return Polygon(fl)
                    if value.endswith('.npz'):
                        with np.load(value, mmap_mode='r') as arr:
                            if hasattr(arr, 'files'):
                                data = arr[arr.files[0]]
                        return Polygon(data)
                    if value.endswith('.json'):
                        with open(value, 'r') as f:
                            data = json.load(f)
                        return from_geojson(json.dumps(data))
                except Exception as e:
                    raise e
            try:
                return from_wkt(value)
            except Exception:
                try:
                    return from_geojson(value)
                except Exception as e:
                    raise e

        return value
