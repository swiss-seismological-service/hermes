
from seismostats import Catalog

from hermes.schemas import SeismicEvent


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
