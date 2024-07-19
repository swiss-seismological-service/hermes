import json
import os

import pandas as pd
from seismostats import Catalog

from hermes.io.catalog import (deserialize_catalog,
                               serialize_seismostats_catalog)

MODULE_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data')


class TestCatalog:
    def test_catalog_serialization(self):
        qml_path = os.path.join(MODULE_LOCATION, 'quakeml.xml')
        catalog = Catalog.from_quakeml(qml_path,
                                       include_uncertainties=True,
                                       include_quality=True)

        for _ in range(6):
            catalog = pd.concat([catalog, catalog], ignore_index=True, axis=0)

        events = serialize_seismostats_catalog(catalog)

        assert events[0]['magnitude_value'] == 2.510115344

    def test_deserialize_catalog(self):
        events = \
            '{"time_value": "2021-12-30T07:43:14", "latitude_value": ' \
            '46.05144527, "latitude_uncertainty": "0.1222628824", ' \
            '"longitude_value": 7.388024848, "longitude_uncertainty": ' \
            '"0.1007121534", "depth_value": 1181.640625, '\
            '"depth_uncertainty": "274.9552879", "magnitude_value": ' \
            '2.510115344, "magnitude_uncertainty": "0.23854491", ' \
            '"magnitude_type": "MLhc"}, {"time_value": ' \
            '"2021-12-25T14:49:40", "latitude_value": 47.37175484, ' \
            '"latitude_uncertainty": "0.1363265577", "longitude_value": ' \
            '6.917056725,"longitude_uncertainty": "0.1277685645", ' \
            '"depth_value": 3364.257812, "depth_uncertainty": ' \
            '"1036.395075", "magnitude_value": 3.539687307, ' \
            '"magnitude_uncertainty": "0.272435385", "magnitude_type": "MLhc"}'

        events = json.loads(f'[{events}]')

        # This is basically already the test for the deserialization
        deserialized = deserialize_catalog(events)

        assert deserialized[0].magnitude_value == 2.510115344
