import json
import os
from datetime import datetime, timedelta

import pandas as pd
from seismostats import Catalog

from hermes.io.catalog import (CatalogDataSource, deserialize_catalog,
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

    def test_get_catalog_from_file(self):
        qml_path = os.path.join(MODULE_LOCATION, 'quakeml.xml')

        starttime = '2021-12-27T00:00:00'
        endtime = '2021-12-31T00:00:00'
        starttime_dt = datetime.fromisoformat(starttime)
        endtime_dt = datetime.fromisoformat(endtime)

        catalog = CatalogDataSource.from_file(qml_path)
        assert len(catalog.catalog) == 2

        assert catalog.get_catalog(starttime_dt, endtime_dt).equals(
            catalog.get_catalog(starttime, endtime))

        assert len(catalog.get_catalog(starttime_dt
                   + timedelta(days=1), endtime_dt)) == 1

        assert len(catalog.get_catalog(endtime=endtime_dt
                   - timedelta(days=1))) == 1

        assert catalog.get_quakeml() == catalog.catalog.to_quakeml()
