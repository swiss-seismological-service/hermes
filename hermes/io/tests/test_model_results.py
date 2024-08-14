import os
from unittest.mock import MagicMock

import pandas as pd
from seismostats import ForecastCatalog
from shapely import from_wkt

from hermes.io.model_results import save_forecast_catalog_to_repositories

MODULE_LOCATION = os.path.dirname(os.path.abspath(__file__))


def test_save_forecast_catalog_to_repositories():
    catalog_path = os.path.join(
        MODULE_LOCATION, '../../repositories/tests/data/catalog.parquet.gzip')

    catalog = ForecastCatalog(pd.read_parquet(catalog_path))
    catalog.starttime = pd.Timestamp('2022-01-01')
    catalog.endtime = pd.Timestamp('2022-01-31')
    catalog.bounding_polygon = from_wkt(
        'POLYGON ((45.7 5.85, 47.9 5.85, 47.9 10.6, 45.7 10.6, 45.7 5.85))')

    save_forecast_catalog_to_repositories(MagicMock(), catalog)
