import json
import urllib.parse
from copy import deepcopy
from datetime import datetime

import requests
from hydws.parser import BoreholeHydraulics
from prefect import flow, get_run_logger, task

from hermes.utils.url import add_query_params


class HydraulicsDataSource:
    @task
    def __init__(self,
                 borehole_hydraulics: BoreholeHydraulics | None = None) \
            -> None:
        """
        Provides a common interface to access seismic event
        data from different sources.

        Should in most cases be initialized using class methods
        according to the source of the data.

        Args:
            catalog: Catalog object.
            starttime: Start time of the catalog.
            endtime: End time of the catalog

        Returns:
            CatalogDataSource object
        """
        self._logger = get_run_logger()
        self.borehole_hydraulics = borehole_hydraulics

    @classmethod
    def from_uri(cls,
                 uri,
                 starttime: datetime | None = None,
                 endtime: datetime | None = None) -> 'HydraulicsDataSource':

        if uri.startswith('file://'):
            catalog = cls.from_file(uri, starttime, endtime)
        elif uri.startswith('http://') or uri.startswith('https://'):
            catalog = cls.from_hydws(uri, starttime, endtime)
        else:
            raise ValueError(
                f'URI scheme of catalog source not supported: {uri}')

        return catalog

    @classmethod
    @flow
    def from_hydws(cls,
                   url: str,
                   starttime: datetime,
                   endtime: datetime) -> tuple['HydraulicsDataSource', int]:
        """
        Initialize a HydraulicsDataSource from a hydws url.

        Args:
            url: URL to the hydws service.
            starttime: Start time of the hydraulic data.
            endtime: End time of the hydraulic data.

        Returns:
            HydraulicsDataSource object
        """
        hds = cls()

        hds._logger.info('Requesting hydraulics from hydraulic webservice:')

        response = hds._request_text(
            url,
            level='hydraulic',
            starttime=starttime.strftime('%Y-%m-%dT%H:%M:%S'),
            endtime=endtime.strftime('%Y-%m-%dT%H:%M:%S'))

        hydraulics = BoreholeHydraulics(json.loads(response[0]))

        hds._logger.info(f'Received response from {url} '
                         f'with status code {response[1]}.')

        hds.borehole_hydraulics = hydraulics

        return hds

    @classmethod
    @task
    def from_file(cls,
                  file_path: str,
                  starttime: datetime | None = None,
                  endtime: datetime | None = None,
                  format: str = 'hydjson') -> 'HydraulicsDataSource':
        """
        Initialize a CatalogDataSource from a file.

        Args:
            file_path: Path to the file.
            starttime: Start time of the catalog.
            endtime: End time of the catalog.
            format: Format of the file.

        Returns:
            CatalogDataSource object
        """
        hds = cls()

        file_path = urllib.parse.urlparse(file_path)
        file_path = urllib.parse.unquote(file_path.path)

        hds._logger.info(
            f'Loading hydraulics from file (file_path={file_path}).')

        if format == 'hydjson':
            with open(file_path, 'rb') as f:
                hydraulics = json.load(f)
        else:
            raise NotImplementedError(f'Format {format} not supported.')

        hydraulics = BoreholeHydraulics(hydraulics)

        if starttime or endtime:
            hydraulics = hydraulics.query_datetime(starttime, endtime)

        hds._logger.info(
            f'Loaded hydraulics from file (file_path={file_path}).')

        hds.borehole_hydraulics = hydraulics

        return hds

    def get_hydraulics(self,
                       starttime: datetime | None = None,
                       endtime: datetime | None = None) -> BoreholeHydraulics:
        """
        Get hydraulics data.

        Args:
            starttime: Start time of the hydraulic data.
            endtime: End time of the hydraulic data.

        Returns:
            BoreholeHydraulics object
        """

        if starttime or endtime:
            return self.borehole_hydraulics.query_datetime(starttime, endtime)

        return deepcopy(self.borehole_hydraulics)

    def get_json(self,
                 starttime: datetime | None = None,
                 endtime: datetime | None = None) -> dict:
        """
        Get hydraulics data as a dictionary.

        Args:
            starttime: Start time of the hydraulic data.
            endtime: End time of the hydraulic data.

        Returns:
            dict
        """

        if starttime or endtime:
            hyd = self.borehole_hydraulics.query_datetime(starttime, endtime)
            return json.dumps(hyd.to_json())

        return json.dumps(self.borehole_hydraulics.to_json())

    @task(retries=3,
          retry_delay_seconds=3)
    def _request_text(self, url: str, timeout: int = 300, **kwargs) \
            -> tuple[str, int]:
        """
        Request text from a URL and raise for status.

        Args:
            url: URL to request.
            timeout: Timeout for the request.

        Returns:
            response text, status code.
        """

        for key, value in kwargs.items():
            if isinstance(value, datetime):
                kwargs[key] = value.strftime('%Y-%m-%dT%H:%M:%S')

        url = add_query_params(url, **kwargs)

        self._logger.info(f'Requesting text from {url}.')

        response = requests.get(url, timeout=timeout)

        response.raise_for_status()

        return response.text, response.status_code
