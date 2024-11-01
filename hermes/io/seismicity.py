import time
import urllib.parse
from datetime import datetime

import pandas as pd
from prefect import flow, task
from seismostats import Catalog
from typing_extensions import Self

from hermes.io.datasource import DataSource
from hermes.utils.dateutils import generate_date_ranges
from hermes.utils.url import add_query_params


class SeismicDataSource(DataSource[Catalog]):
    @classmethod
    @task
    def from_file(cls,
                  file_path: str,
                  starttime: datetime | None = None,
                  endtime: datetime | None = None,
                  format: str = 'quakeml') -> Self:
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
        cds = cls()

        file_path = urllib.parse.urlparse(file_path)
        file_path = urllib.parse.unquote(file_path.path)

        cds._logger.info(
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

        cds._logger.info(
            f'Loaded seismic catalog from file (file_path={file_path}).')

        cds.catalog = catalog

        return cds

    @classmethod
    @flow
    def from_ws(cls,
                url: str,
                starttime: datetime,
                endtime: datetime) -> Self:
        """
        Initialize a CatalogDataSource from a FDSNWS URL.

        Args:
            url: FDSNWS URL.
            starttime: Start time of the catalog.
            endtime: End time of the catalog.

        Returns:
            CatalogDataSource object, status code.
        """
        cds = cls()

        cds._logger.info('Requesting seismic catalog from fdsnws-event:')

        date_ranges = generate_date_ranges(starttime, endtime)

        if len(date_ranges) > 1:
            cds._logger.info(
                f'Requesting catalog in {len(date_ranges)} parts.')

        urls = [add_query_params(url,
                                 starttime=start.strftime('%Y-%m-%dT%H:%M:%S'),
                                 endtime=end.strftime('%Y-%m-%dT%H:%M:%S'))
                for start, end in date_ranges]

        tasks = []
        for u in urls:
            tasks.append(cds._request_text.submit(u))
            time.sleep(0.5)

        parts = [task.result() for task in tasks]

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

        cds._logger.info(f'Received response from {url} '
                         f'with status code {part[1]}.')

        cds.catalog = catalog

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
            return self.catalog.loc[
                (self.catalog['time'] >= starttime if starttime else True)
                & (self.catalog['time'] <= endtime if endtime else True)
            ].copy()
        return self.catalog.copy()
