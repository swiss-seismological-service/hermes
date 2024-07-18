import os

import pandas as pd
from seismostats import Catalog

from hermes.io.catalog import deserialize_seismostats_catalog

MODULE_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data')


class TestCatalog:
    def test_catalog_deserialization(self):
        catalog = Catalog.from_quakeml(os.path.join(MODULE_LOCATION,
                                                    'quakeml.xml'))
        catalog = catalog.strip()

        for _ in range(15):
            catalog = pd.concat([catalog, catalog], ignore_index=True, axis=0)
        print(len(catalog))

        # import time
        # now = time.time()
        # print('Start')
        events = deserialize_seismostats_catalog(catalog)
        # print(f'Time taken: {time.time() - now}')

        assert events[0].magnitude_value == 2.510115344

    def test_catalog_serialization(self):
        pass
