import os
import pickle
from unittest.mock import MagicMock, patch

import pandas as pd
from seismostats import ForecastCatalog
from shapely import from_wkt

from hermes.actions.save_results import (
    save_forecast_catalog_to_repositories,
    save_forecast_grrategrid_to_repositories)

MODULE_LOCATION = os.path.dirname(os.path.abspath(__file__))


@patch('hermes.actions.save_results.TimeStepRepository.get_or_create',
       autospec=True)
@patch('hermes.actions.save_results.GridCellRepository.get_or_create',
       autospec=True)
@patch('hermes.actions.save_results.ModelResultRepository.batch_create',
       autospec=True)
@patch('hermes.actions.save_results.SeismicEventRepository.'
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
    catalog.depth_min = 0
    catalog.depth_max = 100

    save_forecast_catalog_to_repositories(MagicMock(), None, None, catalog)

    # TODO: Add assertions


@patch('hermes.actions.save_results.TimeStepRepository.get_or_create',
       autospec=True)
@patch('hermes.actions.save_results.GridCellRepository.get_or_create',
       autospec=True)
@patch('hermes.actions.save_results.ModelResultRepository.batch_create',
       autospec=True)
@patch('hermes.actions.save_results.GRParametersRepository.'
       'create_from_forecast_grrategrid',
       autospec=True)
def test_save_grrategrid_to_repositories(mock_grparameters_repo,
                                         mock_model_result_repo,
                                         mock_grid_cell_repo,
                                         mock_time):
    catalog_path = os.path.join(
        MODULE_LOCATION,
        '../../repositories/tests/data/forecastgrrategrid.pkl')

    with open(catalog_path, 'rb') as f:
        rategrid = pickle.load(f)

    rategrid = rategrid[-1]

    rategrid2 = rategrid.copy()
    rategrid2[['longitude_min', 'longitude_max',
               'latitude_min', 'latitude_max']] = \
        rategrid2[['longitude_min', 'longitude_max',
                   'latitude_min', 'latitude_max']] + 1

    rategrid = pd.concat([rategrid, rategrid2])

    save_forecast_grrategrid_to_repositories(MagicMock(), None, None, rategrid)

    # TODO: Add assertions
