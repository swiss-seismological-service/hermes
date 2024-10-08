from datetime import datetime
from unittest.mock import MagicMock, patch

from hermes.flows.catalog_readers import get_catalog


class TestCatalogReader:
    @patch('hermes.flows.catalog_readers.CatalogDataSource.from_file',
           autocast=True)
    def test_get_file_catalog(self, mock_data_source: MagicMock):

        source = MagicMock()
        source.get_catalog.return_value = 'test_catalog'
        mock_data_source.return_value = source

        catalog = get_catalog('file:///home/user/file.txt',
                              datetime(2021, 1, 1), datetime(2021, 1, 2))
        assert catalog == 'test_catalog'
        mock_data_source.assert_called_with('/home/user/file.txt')
        source.get_catalog.assert_called_with(datetime(2021, 1, 1),
                                              datetime(2021, 1, 2))

    @patch('hermes.flows.catalog_readers.CatalogDataSource.from_fdsnws',
           autocast=True)
    def test_get_fdsnws_catalog(self, mock_data_source: MagicMock):

        source = MagicMock()
        source.get_catalog.return_value = 'test_catalog'
        mock_data_source.return_value = (source, 200)

        catalog = get_catalog('http://example.com',
                              datetime(2021, 1, 1), datetime(2021, 1, 2))
        assert catalog == 'test_catalog'
        mock_data_source.assert_called_with('http://example.com',
                                            datetime(2021, 1, 1),
                                            datetime(2021, 1, 2))
        source.get_catalog.assert_called_once()
