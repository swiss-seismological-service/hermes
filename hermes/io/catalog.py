
import logging
from datetime import datetime

import pandas as pd
import requests
from prefect import flow, task
from seismostats import Catalog
from shapely import Point

from hermes.repositories.types import shapely_to_db
from hermes.schemas import SeismicEvent
from hermes.schemas.base import Model
from hermes.utils.dateutils import generate_date_ranges
from hermes.utils.url import add_query_params


def serialize_seismostats_catalog(catalog: Catalog,
                                  model: Model = SeismicEvent) -> list[dict]:
    """
    Serialize a Seismostats Catalog object to a list of dictionaries.

    Args:
        catalog: Catalog object with the events.
        model: Model object to serialize the events to.
    Returns:
        List of dictionaries, each dictionary representing an event.
    """
    # rename value columns to match 'RealQuantity" fields
    column_renames = {col: f'{col}_value' for col in Catalog._required_cols}
    catalog = catalog.rename(columns=column_renames)

    if 'longitude_value' in catalog.columns and \
            'latitude_value' in catalog.columns:
        catalog['coordinates'] = catalog.apply(
            lambda row: shapely_to_db(
                Point(row['longitude_value'], row['latitude_value'])),
            axis=1)

    # only keep columns that are in the model
    catalog = catalog[[c for c in catalog.columns if c in list(
        model.model_fields)]]

    # pandas to_dict method for very fast serialization
    events = catalog.to_dict(orient='records')

    return events


def deserialize_catalog(events: list[dict]) -> list[SeismicEvent]:
    """
    Deserialize a list of dictionaries to a list of SeismicEvent objects.

    Args:
        events: List of dictionaries, each dictionary representing an event.

    Returns:
        List of SeismicEvent objects.
    """
    events = [SeismicEvent(**c) for c in events]

    return events


class CatalogDataSource:
    def __init__(self,
                 catalog: Catalog | None = None,
                 starttime: datetime | None = None,
                 endtime: datetime | None = None) -> None:
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
        self._logger = logging.getLogger(__name__)
        self.catalog = catalog
        self.starttime = starttime
        self.endtime = endtime

    @classmethod
    def from_file(cls,
                  file_path: str,
                  starttime: datetime | None = None,
                  endtime: datetime | None = None,
                  format: str = 'quakeml') -> 'CatalogDataSource':
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

        return cls(catalog=catalog,
                   starttime=starttime or catalog['time'].min(),
                   endtime=endtime or catalog['time'].max())

    @classmethod
    @flow
    def from_fdsnws(cls,
                    url: str,
                    starttime: datetime,
                    endtime: datetime) -> tuple['CatalogDataSource', int]:
        """
        Initialize a CatalogDataSource from a FDSNWS URL.

        Args:
            url: FDSNWS URL.
            starttime: Start time of the catalog.
            endtime: End time of the catalog.

        Returns:
            CatalogDataSource object, status code.
        """

        date_ranges = generate_date_ranges(starttime, endtime)

        urls = [add_query_params(url,
                                 starttime=start.strftime('%Y-%m-%dT%H:%M:%S'),
                                 endtime=end.strftime('%Y-%m-%dT%H:%M:%S'))
                for start, end in date_ranges]

        tasks = [cls._request_text.submit(url) for url in urls]
        parts = [task.result() for task in tasks]

        catalog = Catalog()
        status_code = 200

        for part in parts:
            if 200 < part[1] <= 299:
                status_code = part[1]
                continue

            catalog = pd.concat([
                catalog if not catalog.empty else None,
                Catalog.from_quakeml(part[0],
                                     include_uncertainties=True,
                                     include_ids=True,
                                     include_quality=True)],
                                ignore_index=True,
                                axis=0).reset_index(drop=True)

        catalog = catalog.sort_values('time')

        return cls(catalog=catalog,
                   starttime=starttime,
                   endtime=endtime), status_code

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
        starttime = starttime or self.starttime
        endtime = endtime or self.endtime

        if starttime < self.starttime or endtime > self.endtime:
            raise ValueError(
                'Requested time range is outside of '
                'the catalog time range.')

        return self.catalog.loc[
            (self.catalog['time'] >= starttime)
            & (self.catalog['time'] <= endtime)
        ]

    @classmethod
    @task
    def _request_text(cls, url: str, timeout: int = 60, **kwargs) \
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

        response = requests.get(url, timeout=timeout)

        response.raise_for_status()

        return response.text, response.status_code
