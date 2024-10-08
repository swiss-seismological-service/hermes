import os
from unittest.mock import MagicMock, patch

import pandas as pd
from seismostats import ForecastCatalog
from shapely import from_wkt

from hermes.io.model_results import save_forecast_catalog_to_repositories

MODULE_LOCATION = os.path.dirname(os.path.abspath(__file__))


@patch('hermes.io.model_results.TimeStepRepository.get_or_create',
       autospec=True)
@patch('hermes.io.model_results.GridCellRepository.get_or_create',
       autospec=True)
@patch('hermes.io.model_results.ModelResultRepository.batch_create',
       autospec=True)
@patch('hermes.io.model_results.SeismicEventRepository.'
       'create_from_forecast_catalog',
       autospec=True)
def test_save_forecast_catalog_to_repositories(mock_seismic_event_repo,
                                               mock_model_result_repo,
                                               mock_grid_cell_repo,
                                               mock_time):
    catalog_path = os.path.join(
        MODULE_LOCATION, '../../repositories/tests/data/catalog.parquet.gzip')

    catalog = ForecastCatalog(pd.read_parquet(catalog_path))
    catalog.starttime = pd.Timestamp('2022-01-01')
    catalog.endtime = pd.Timestamp('2022-01-31')
    catalog.bounding_polygon = from_wkt(
        'POLYGON ((45.7 5.85, 47.9 5.85, 47.9 10.6, 45.7 10.6, 45.7 5.85))')

    save_forecast_catalog_to_repositories(MagicMock(), None, None, catalog)
