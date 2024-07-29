import os

from shapely import Polygon

from hermes.schemas.project_schemas import ForecastSeries

PATH_RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'data')

GEOJSON = {"bounding_polygon": {"type": "Polygon", "coordinates": [
    [[30.0, 10.0], [40.0, 40.0], [20.0, 40.0], [10.0, 20.0], [30.0, 10.0]]]}}
WKT = {"bounding_polygon": "POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))"}
NPZ = {"bounding_polygon": os.path.join(PATH_RESOURCES, 'polygon.npz')}
NPY = {"bounding_polygon": os.path.join(PATH_RESOURCES, 'polygon.npy')}
JSON = {"bounding_polygon": os.path.join(PATH_RESOURCES, 'polygon.json')}
REFERENCE = Polygon([(30.0, 10.0), (40.0, 40.0), (20.0, 40.0),
                     (10.0, 20.0), (30.0, 10.0)])


def test_forecastseries():
    result_json = ForecastSeries(**GEOJSON)
    assert result_json.bounding_polygon == REFERENCE

    result_wkt = ForecastSeries(**WKT)
    assert result_wkt.bounding_polygon == REFERENCE

    result_npz = ForecastSeries(**NPZ)
    assert result_npz.bounding_polygon == REFERENCE

    result_npy = ForecastSeries(**NPY)
    assert result_npy.bounding_polygon == REFERENCE

    result_json = ForecastSeries(**JSON)
    assert result_json.bounding_polygon == REFERENCE
