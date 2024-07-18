
from seismostats import Catalog

from hermes.schemas import SeismicEvent


def deserialize_seismostats_catalog(catalog: Catalog) -> list[SeismicEvent]:

    column_renames = {col: f'{col}_value' for col in Catalog._required_cols}

    catalog = catalog.rename(columns=column_renames)
    events = catalog.to_dict(orient='records')

    events = [SeismicEvent.parse_obj(c) for c in events]

    # event_dicts = [e.model_dump() for e in events]

    return events
