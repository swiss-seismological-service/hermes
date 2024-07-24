
import logging
from datetime import datetime
from typing import TypeVar

import requests
from seismostats import Catalog

from hermes.schemas import SeismicEvent
from hermes.utils.url import add_query_params


def serialize_seismostats_catalog(catalog: Catalog) -> list[dict]:
    """
    Serialize a Seismostats Catalog object to a list of dictionaries.

    Args:
        catalog: Catalog object with the events.

    Returns:
        List of dictionaries, each dictionary representing an event.
    """
    # rename value columns to match 'RealQuantity" fields
    column_renames = {col: f'{col}_value' for col in Catalog._required_cols}
    catalog = catalog.rename(columns=column_renames)

    # only keep columns that are in the SeismicEvent model
    catalog = catalog[[c for c in catalog.columns if c in list(
        SeismicEvent.model_fields)]]

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


T = TypeVar('T', bound='CatalogDataSource')


class CatalogDataSource:
    def __init__(self,
                 catalog: Catalog | None = None,
                 starttime: datetime | None = None,
                 endtime: datetime | None = None) -> None:
        self._logger = logging.getLogger(__name__)
        self.catalog = catalog
        self.starttime = starttime
        self.endtime = endtime

    @classmethod
    def from_file(cls, file_path: str, format: str = 'quakeml') -> T:
        if format == 'quakeml':
            catalog = Catalog.from_quakeml(file_path,
                                           include_uncertainties=True,
                                           include_ids=True,
                                           include_quality=True)
        else:
            raise NotImplementedError(f'Format {format} not supported.')

        return cls(catalog=catalog,
                   starttime=catalog['time'].min(),
                   endtime=catalog['time'].max())

    @classmethod
    def from_fdsnws(cls,
                    url: str,
                    starttime: datetime,
                    endtime: datetime) -> T:
        url = add_query_params(
            url,
            starttime=starttime.strftime('%Y-%m-%dT%H:%M:%S'),
            endtime=endtime.strftime('%Y-%m-%dT%H:%M:%S'))

        response = cls.request_text(url)
        catalog = Catalog.from_quakeml(response.text,
                                       include_uncertainties=True,
                                       include_ids=True,
                                       include_quality=True)
        return cls(catalog=catalog, starttime=starttime, endtime=endtime)

    def get_quakeml(self,
                    starttime: str | datetime | None = None,
                    endtime: str | datetime | None = None) -> Catalog:

        cat = self.get_catalog(starttime=starttime, endtime=endtime)

        return cat.to_quakeml()

    def get_catalog(self,
                    starttime: str | datetime | None = None,
                    endtime: str | datetime | None = None) -> Catalog:

        if starttime or endtime:
            return self.catalog.loc[
                (self.catalog['time'] >= starttime if starttime else True)
                & (self.catalog['time'] <= endtime if endtime else True)
            ]

        return self.catalog

    @classmethod
    def request_text(cls, url: str, timeout: int = 60) -> str:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
