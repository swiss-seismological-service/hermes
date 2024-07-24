from datetime import datetime

from prefect import flow, get_run_logger, task

from hermes.io.catalog import CatalogDataSource
from hermes.schemas.types import DatetimeString
from hermes.utils.url import add_query_params


@task
def get_catalog_fdsnws(url: str) -> str:
    logger = get_run_logger()

    logger.info(f'Requesting seismic catalog from fdsnws-event (url={url}).')

    response = CatalogDataSource.request_text(url)

    logger.info(f'Received response from {url} '
                f'with status code {response.status_code}.')

    return response


@task
def get_catalog_file(file_path: str) -> str:
    logger = get_run_logger()

    logger.info(f'Loading seismic catalog from file (file_path={file_path}).')

    logger.info(f'Loaded seismic catalog from file (file_path={file_path}).')

    return catalog


@flow(name="Get Seismicity Observation")
def get_catalog(starttime: DatetimeString, endtime: DatetimeString, url: str):

    url = add_query_params(url, starttime=starttime, endtime=endtime)

    catalog = get_catalog_fdsnws(url)

    return catalog


if __name__ == "__main__":

    url = "http://arclink.ethz.ch/fdsnws/event/1/query?minmagnitude=2"

    starttime = datetime(2024, 7, 1)

    endtime = datetime.now()

    catalog = get_catalog(starttime, endtime, url)
