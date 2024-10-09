import urllib.parse
from datetime import datetime

from prefect import get_run_logger, task
from seismostats import Catalog

from hermes.io.catalog import CatalogDataSource


@task
def get_catalog_fdsnws(url: str,
                       starttime: datetime,
                       endtime: datetime) -> str:
    logger = get_run_logger()

    logger.info(f'Requesting seismic catalog from fdsnws-event (url={url}).')

    source, status_code = CatalogDataSource.from_fdsnws(
        url, starttime, endtime)

    response = source.get_catalog()

    logger.info(f'Received response from {url} '
                f'with status code {status_code}.')

    return response


@task
def get_catalog_file(file_path: str,
                     starttime: datetime | None = None,
                     endtime: datetime | None = None) -> str:
    logger = get_run_logger()

    file_path = urllib.parse.urlparse(file_path)
    file_path = urllib.parse.unquote(file_path.path)

    logger.info(f'Loading seismic catalog from file (file_path={file_path}).')

    source = CatalogDataSource.from_file(file_path)
    catalog = source.get_catalog(starttime, endtime)

    logger.info(f'Loaded seismic catalog from file (file_path={file_path}).')

    return catalog


@task
def get_catalog(url: str, starttime: datetime, endtime: datetime) -> Catalog:

    if endtime < starttime:
        raise ValueError('End time must be greater than start time.')

    if url.startswith('file://'):
        catalog = get_catalog_file(url, starttime, endtime)
    elif url.startswith('http://') or url.startswith('https://'):
        catalog = get_catalog_fdsnws(url, starttime, endtime)
    else:
        raise ValueError(f'URI scheme of catalog source not supported: {url}')

    return catalog


# if __name__ == '__main__':
#     # make a request to the usgs service
#     cat = get_catalog(url='https://earthquake.usgs.gov/fdsnws/event/1/query',
#                       starttime=datetime(2021, 1, 1),
#                       endtime=datetime(2021, 1, 1))
