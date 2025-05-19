import numpy as np
import pandas as pd
from seismostats import Catalog, ForecastGRRateGrid
from shapely import Point

from hermes.repositories.types import db_to_shapely, shapely_to_db
from hermes.schemas import GRParameters, SeismicEvent
from hermes.schemas.base import Model

CATALOG_QUANTITY_FIELDS = ['latitude',
                           'longitude', 'depth', 'magnitude', 'time']
RATEGRID_QUANTITY_FIELDS = ['number_events', 'b', 'a', 'alpha', 'mc']


def serialize_seismostats_grrategrid(
        rategrid: ForecastGRRateGrid,
        model: type[Model] = GRParameters) -> list[dict]:
    """
    Serialize a Seismostats ForecastGRRateGrid object to a list of dicts.

    Args:
        rategrid: ForecastGRRateGrid object.
        model: Model object to serialize the rategrid to.

    Returns:
        List of dictionaries, each dictionary representing a rategrid.
    """

    column_renames = {col: f'{col}_value' for col in RATEGRID_QUANTITY_FIELDS}

    rategrid = rategrid.rename(columns=column_renames)

    rategrid = rategrid[[c for c in rategrid.columns if c in list(
        model.model_fields)]]

    return rategrid.to_dict(orient='records')


def deserialize_seismostats_grrategrid(
        rategrid: pd.DataFrame) -> ForecastGRRateGrid:
    """
    Deserialize a pd.DataFrame directly from the DB model to a
    Seismostats ForecastGRRateGrid object.

    Args:
        rategrid: List of dictionaries representing the rategrid.
        model: Model object to deserialize the rategrid to.

    Returns:
        ForecastGRRateGrid object.
    """
    if rategrid.empty:
        return ForecastGRRateGrid()
    # rename value columns to match 'RealQuantity" fields
    column_renames = {f'{col}_value': col for col in RATEGRID_QUANTITY_FIELDS}
    rategrid = rategrid.rename(columns=column_renames)

    boundingbox = deserialize_geom_column(rategrid['geom'])
    rategrid = pd.concat([boundingbox, rategrid], axis=1)

    rategrid = rategrid.drop(columns=['oid', 'modelresult_oid', 'geom'])
    rategrid = rategrid.dropna(axis=1, how='all')

    return ForecastGRRateGrid(rategrid)


def deserialize_geom_column(geom_col: pd.Series) -> pd.DataFrame:
    """
    Deserialize the geometry column of a rategrid DataFrame.

    Args:
        rategrid: DataFrame with a geometry column.

    Returns:
        DataFrame with the geometry column deserialized.
    """
    if geom_col.empty:
        return geom_col

    geom_col = geom_col.apply(
        lambda x: db_to_shapely(x) if x is not None else None)
    bounds = geom_col.apply(
        lambda geom: geom.bounds if geom is not None else (None, None,
                                                           None, None))
    bounding_cols = pd.DataFrame(bounds.tolist(), columns=[
        'longitude_min', 'latitude_min', 'longitude_max', 'latitude_max'
    ])
    return bounding_cols


def serialize_seismostats_catalog(
    catalog: Catalog,
        model: type[Model] = SeismicEvent) -> list[dict]:
    """
    Serialize a Seismostats Catalog object to a list of dictionaries.

    Args:
        catalog: Catalog object with the events.
        model: Model object to serialize the events to.
    Returns:
        List of dictionaries, each dictionary representing an event.
    """

    # rename value columns to match 'RealQuantity" fields
    column_renames = {col: f'{col}_value' for col in CATALOG_QUANTITY_FIELDS}
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

    # replace NaNs with None for database compatibility
    catalog = catalog.replace({pd.NA: None,
                               np.nan: None})

    events = catalog.to_dict(orient='records')

    return events
