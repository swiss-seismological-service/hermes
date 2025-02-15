import time
from datetime import datetime

import pandas as pd
from prefect import task
from seismostats import Catalog
from typing_extensions import Self

from hermes.io.datasource import DataSource
from hermes.utils.dateutils import generate_date_ranges
from hermes.utils.url import add_query_params


class SeismicityDataSource(DataSource[Catalog]):
    @classmethod
    @task(name='SeismicityDataSource.from_file')
    def from_file(cls,
                  file_path: str,
                  starttime: datetime | None = None,
                  endtime: datetime | None = None,
                  format: str = 'quakeml') -> Self:
        """
        Initialize a SeismicityDataSource from a file.

        Args:
            file_path: Path to the file.
            starttime: Start time of the catalog.
            endtime: End time of the catalog.
            format: Format of the file.

        Returns:
            SeismicityDataSource object
        """
        cds = cls()

        cds.logger.info(
            f'Loading seismic catalog from file (file_path={file_path}).')

        if format == 'quakeml':
            catalog = Catalog.from_quakeml(file_path,
                                           include_uncertainties=True,
                                           include_ids=True,
                                           include_quality=True)
        else:
            raise NotImplementedError(f'Format {format} not supported.')

        if starttime or endtime:
            catalog = catalog.loc[
                (catalog['time'] >= starttime if starttime else True)
                & (catalog['time'] <= endtime if endtime else True)
            ]

        cds.logger.info(
            f'Loaded seismic catalog from file (file_path={file_path}).')

        cds.data = catalog

        return cds

    @classmethod
    @task(name='SeismicityDataSource.from_ws')
    def from_ws(cls,
                url: str,
                starttime: datetime,
                endtime: datetime) -> Self:
        """
        Initialize a SeismicityDataSource from a FDSNWS URL.

        Args:
            url: FDSNWS URL.
            starttime: Start time of the catalog.
            endtime: End time of the catalog.

        Returns:
            SeismicityDataSource object.
        """
        cds = cls()

        cds.logger.info('Requesting seismic catalog from fdsnws-event:')

        date_ranges = generate_date_ranges(starttime, endtime)

        if len(date_ranges) > 1:
            cds.logger.info(
                f'Requesting catalog in {len(date_ranges)} parts.')

        urls = [add_query_params(url,
                                 starttime=start.strftime('%Y-%m-%dT%H:%M:%S'),
                                 endtime=end.strftime('%Y-%m-%dT%H:%M:%S'))
                for start, end in date_ranges]

        try:
            tasks = []
            for u in urls:
                time.sleep(0.5)
                tasks.append(cds._request_text.submit(u))
            parts = [task.result() for task in tasks]
        except RuntimeError:
            parts = [cds._request_text(u) for u in urls]

        catalog = Catalog()

        for part in parts:
            catalog = pd.concat([
                catalog if not catalog.empty else None,
                Catalog.from_quakeml(part[0],
                                     include_uncertainties=True,
                                     include_ids=True,
                                     include_quality=True)],
                                ignore_index=True,
                                axis=0).reset_index(drop=True)

        catalog = catalog.sort_values('time')

        if parts:
            cds.logger.info(f'Received response from {url} '
                            f'with status code {part[1]}.')
        else:
            cds.logger.warning('Observed seismicity period has zero length.'
                               ' No data was requested.')

        cds.data = catalog

        return cds

    def get_quakeml(self,
                    starttime: datetime | None = None,
                    endtime: datetime | None = None) -> Catalog:
        """
        Get the catalog in QuakeML format.

        Args:
            starttime: Start time of the catalog.
            endtime: End time of the catalog.

        Returns:
            Catalog in QuakeML format
        """
        cat = self.get_catalog(starttime=starttime, endtime=endtime)

        return cat.to_quakeml()

    def get_catalog(self,
                    starttime: datetime | None = None,
                    endtime: datetime | None = None) -> Catalog:
        """
        Get the catalog, optionally filtered by start and end time.

        Args:
            starttime: Filter by starttime.
            endtime: Filter by endtime.

        Returns:
            Catalog object
        """
        if starttime or endtime:
            return self.data.loc[
                (self.data['time'] >= starttime if starttime else True)
                & (self.data['time'] <= endtime if endtime else True)
            ].copy()
        return self.data.copy()
