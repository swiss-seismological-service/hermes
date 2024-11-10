import json
import urllib.parse
from copy import deepcopy
from datetime import datetime

from hydws.parser import BoreholeHydraulics
from prefect import flow, task
from typing_extensions import Self

from hermes.io.datasource import DataSource


class HydraulicsDataSource(DataSource[BoreholeHydraulics]):

    @classmethod
    @flow
    def from_ws(cls,
                url: str,
                starttime: datetime,
                endtime: datetime) -> Self:
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

        hds.data = hydraulics

        return hds

    @classmethod
    @task
    def from_file(cls,
                  file_path: str,
                  starttime: datetime | None = None,
                  endtime: datetime | None = None,
                  format: str = 'hydjson') -> Self:
        """
        Initialize a BoreholeHydraulics object from a file.

        Args:
            file_path: Path to the file.
            starttime: Start time of the catalog.
            endtime: End time of the catalog.
            format: Format of the file.

        Returns:
            BoreholeHydraulics object
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

        hds.data = hydraulics

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
            return self.data.query_datetime(starttime, endtime)

        return deepcopy(self.data)

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
            hyd = self.data.query_datetime(starttime, endtime)
            return json.dumps(hyd.to_json())

        return json.dumps(self.data.to_json())
