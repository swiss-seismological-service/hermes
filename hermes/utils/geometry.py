import json
from pathlib import Path

import numpy as np
from shapely import Polygon, from_geojson, from_wkt


def convert_input_to_polygon(value: str) -> Polygon:
    """
    Try to convert input to a shapely Polygon object.

    Expects to receive a string that can be either a WKT, GeoJSON,
    or a path to a file containing a numpy array.

    Args:
        value: path or string representation of a polygon.

    Returns:
        A shapely Polygon object.
    """
    # path names can at most be 255 characters long
    if len(value) < 255 and Path(value).exists():
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
