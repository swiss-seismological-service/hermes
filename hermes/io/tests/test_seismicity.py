import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from hermes.io.seismicity import CatalogDataSource

MODULE_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data')


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

    @patch('hermes.io.seismicity.requests.get')
    def test_get_catalog_from_fdsnws(self, mock_get):

        with open(os.path.join(MODULE_LOCATION, 'quakeml.xml'), 'r') as f:
            answer = Mock(text=f.read(), status_code=200)

        urls = ['https://mock.com?starttime=2021-12-25T00%3A00%3A00&'
                'endtime=2022-12-25T00%3A00%3A00',
                'https://mock.com?starttime=2022-12-25T00%3A00%3A00&'
                'endtime=2023-01-12T12%3A01%3A03']

        mock_get.return_value = answer

        base_url = 'https://mock.com'
        starttime = datetime(2021, 12, 25)
        endtime = datetime(2023, 1, 12, 12, 1, 3)

        catalog = CatalogDataSource.from_fdsnws(
            base_url, starttime, endtime)

        for url in urls:
            mock_get.assert_any_call(url, timeout=60)

        assert len(catalog.catalog) == 4

    @patch('hermes.io.seismicity.CatalogDataSource.from_file',
           autocast=True)
    @patch('hermes.io.seismicity.CatalogDataSource.from_fdsnws',
           autocast=True)
    def test_get_uri_catalog(self,
                             mock_fdsn_source: MagicMock,
                             mock_file_source: MagicMock):

        CatalogDataSource.from_uri('file:///home/user/file.txt',
                                   datetime(2021, 1, 1),
                                   datetime(2021, 1, 2))

        mock_file_source.assert_called_with('file:///home/user/file.txt',
                                            datetime(2021, 1, 1),
                                            datetime(2021, 1, 2))

        CatalogDataSource.from_uri('http://example.com',
                                   datetime(2021, 1, 1),
                                   datetime(2021, 1, 2))

        mock_fdsn_source.assert_called_with('http://example.com',
                                            datetime(2021, 1, 1),
                                            datetime(2021, 1, 2))

        with pytest.raises(ValueError):
            CatalogDataSource.from_uri('ftp://example.com',
                                       datetime(2021, 1, 1),
                                       datetime(2021, 1, 2))
