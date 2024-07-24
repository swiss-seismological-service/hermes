from datetime import datetime

from prefect import flow, get_run_logger, task

from hermes.io.catalog import CatalogDataSource


@task
def get_catalog_fdsnws(url: str,
                       starttime: datetime,
                       endtime: datetime) -> str:
    logger = get_run_logger()

    logger.info(f'Requesting seismic catalog from fdsnws-event (url={url}).')

    response, status_code = CatalogDataSource.request_text(
        url, starttime=starttime, endtime=endtime)

    logger.info(f'Received response from {url} '
                f'with status code {status_code}.')

    return response


@task
def get_catalog_file(file_path: str,
                     starttime: datetime | None = None,
                     endtime: datetime | None = None) -> str:
    logger = get_run_logger()

    logger.info(f'Loading seismic catalog from file (file_path={file_path}).')

    source = CatalogDataSource.from_file(file_path, starttime, endtime)
    catalog = source.get_catalog()

    logger.info(f'Loaded seismic catalog from file (file_path={file_path}).')

    return catalog


@flow(name="Get Seismicity Observation")
def get_catalog(url: str, starttime: datetime, endtime: datetime):

    catalog = get_catalog_fdsnws(url, starttime, endtime)

    return catalog
