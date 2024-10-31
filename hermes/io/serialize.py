from seismostats import Catalog, ForecastGRRateGrid
from shapely import Point

from hermes.repositories.types import shapely_to_db
from hermes.schemas import GRParameters, SeismicEvent
from hermes.schemas.base import Model


def serialize_seismostats_grrategrid(
        rategrid: ForecastGRRateGrid,
        model: Model = GRParameters) -> list[dict]:
    """
    Serialize a Seismostats ForecastGRRateGrid object to a list of dicts.

    Args:
        rategrid: ForecastGRRateGrid object.
        model: Model object to serialize the rategrid to.

    Returns:
        List of dictionaries, each dictionary representing a rategrid.
    """

    required_cols = ForecastGRRateGrid._required_cols + ['number_events']

    column_renames = {col: f'{col}_value' for col in required_cols}

    rategrid = rategrid.rename(columns=column_renames)

    rategrid = rategrid[[c for c in rategrid.columns if c in list(
        model.model_fields)]]

    return rategrid.to_dict(orient='records')


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
