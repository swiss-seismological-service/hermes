import json
import urllib.parse
from copy import deepcopy
from datetime import datetime

from hydws.parser import BoreholeHydraulics
from prefect import task
from typing_extensions import Self

from hermes.io.datasource import DataSource


class HydraulicsDataSource(DataSource[BoreholeHydraulics]):

    @classmethod
    @task(name='HydraulicsDataSource.from_ws')
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

        hds.logger.info('Requesting hydraulics from hydraulic webservice:')

        response = hds._request_text(
            url,
            level='hydraulic',
            starttime=starttime.strftime('%Y-%m-%dT%H:%M:%S'),
            endtime=endtime.strftime('%Y-%m-%dT%H:%M:%S'))

        hds.logger.info(f'Received response from {url} '
                        f'with status code {response[1]}.')

        hydraulics = BoreholeHydraulics(json.loads(response[0]))

        hds.data = [hydraulics]

        return hds

    @classmethod
    @task(name='HydraulicsDataSource.from_file')
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

        hds.logger.info(
            f'Loading hydraulics from file (file_path={file_path}).')

        if format == 'hydjson':
            with open(file_path, 'rb') as f:
                hydraulics = json.load(f)
        else:
            raise NotImplementedError(f'Format {format} not supported.')

        hds.logger.info(
            f'Loaded hydraulics from file (file_path={file_path}).')

        return cls.from_data(hydraulics, starttime, endtime, hds)

    @classmethod
    def from_data(cls,
                  data: dict | list,
                  starttime: datetime | None = None,
                  endtime: datetime | None = None,
                  hds: Self | None = None) -> Self:
        """
        Initialize a BoreholeHydraulics object from text.

        Args:
            data: List or dict containing the hydraulics data.

        Returns:
            HydraulicDataSource object
        """
        if not hds:
            hds = cls()

        if not isinstance(data, list):
            data = [data]

        data = [BoreholeHydraulics(bh) for bh in data]
        if starttime or endtime:
            data = [bh.query_datetime(starttime, endtime) for bh in data]

        hds.data = data

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
            return [hd.query_datetime(starttime, endtime) for hd in self.data]

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
            hydraulics = [bh.query_datetime(
                starttime, endtime) for bh in self.data]
            return json.dumps([hd.to_json() for hd in hydraulics])

        return json.dumps([hd.to_json() for hd in self.data])
