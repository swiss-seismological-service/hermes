import os
import pickle
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pandas as pd
from numpy.testing import assert_almost_equal
from prefect.testing.utilities import prefect_test_harness
from seismostats import Catalog

from hermes.io.catalog import (CatalogDataSource,
                               serialize_seismostats_catalog,
                               serialize_seismostats_grrategrid)

MODULE_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data')


class TestGRRategrid:
    def test_rategrid_serialization(self):
        rategrid_path = os.path.join(
            MODULE_LOCATION,
            '../../../repositories/tests/data',
            'forecastgrrategrid.pkl')
        with open(rategrid_path, 'rb') as f:
            data = pickle.load(f)

        rategrid = data[-1]

        rategrid = serialize_seismostats_grrategrid(rategrid)
        assert_almost_equal(rategrid[-1]['b_value'], 2.097799, 5)


class TestCatalog:
    def test_catalog_serialization(self):
        qml_path = os.path.join(MODULE_LOCATION, 'quakeml.xml')
        catalog = Catalog.from_quakeml(qml_path,
                                       include_uncertainties=True,
                                       include_quality=True)

        for _ in range(6):
            catalog = pd.concat([catalog, catalog], ignore_index=True, axis=0)

        events = serialize_seismostats_catalog(catalog)

        assert events[0]['magnitude_value'] == 2.510115344


class TestCatalogDataSource:

    def test_get_catalog_from_file(self):
        qml_path = os.path.join(MODULE_LOCATION, 'quakeml.xml')

        starttime = datetime.fromisoformat('2021-12-25T00:00:00')
        endtime = datetime.fromisoformat('2021-12-30T12:00:00')

        catalog = CatalogDataSource.from_file(qml_path, starttime, endtime)

        assert len(catalog.catalog) == 2

        assert len(catalog.get_catalog(starttime
                   + timedelta(days=1), endtime)) == 1

        assert len(catalog.get_catalog(endtime=endtime
                   - timedelta(days=1))) == 1

        assert catalog.get_quakeml() == catalog.catalog.to_quakeml()

    @patch('hermes.io.catalog.requests.get')
    def test_get_catalog_from_fdsnws(self, mock_get):

        with open(os.path.join(MODULE_LOCATION, 'quakeml.xml'), 'r') as f:
            answer = Mock(text=f.read(), status_code=200)

        urls = ['https://mock.com?starttime=2021-12-25T00%3A00%3A00&'
                'endtime=2021-12-31T23%3A59%3A59',
                'https://mock.com?starttime=2022-01-01T00%3A00%3A00&'
                'endtime=2022-12-31T23%3A59%3A59',
                'https://mock.com?starttime=2023-01-01T00%3A00%3A00&'
                'endtime=2023-01-12T12%3A01%3A03']

        mock_get.return_value = answer

        base_url = 'https://mock.com'
        starttime = datetime(2021, 12, 25)
        endtime = datetime(2023, 1, 12, 12, 1, 3)

        with prefect_test_harness():
            catalog = CatalogDataSource.from_fdsnws(
                base_url, starttime, endtime)

        for url in urls:
            mock_get.assert_any_call(url, timeout=60)

        assert len(catalog[0].catalog) == 6
