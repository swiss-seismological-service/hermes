# -*- encoding: utf-8 -*-
"""
Get event data from an ObsPy Catalog

Copyright (C) 2015, ETH Zurich - Swiss Seismological Service SED

"""


class ObsPyCatalogImporter:

    def __init__(self, catalog):
        self.catalog = catalog

    def __iter__(self):
        """
        Iterator for the importer. Parses events and returns the data in a
        tuple.

        The tuple contains the absolute date of the event and a dictionary
        with the location and magnitude of the event.

        """
        for event in self.catalog:
            # TODO: get origin lat/long and convert to cartesian coordinates
            origin = event.preferred_origin()
            magnitude = event.preferred_magnitude()
            if not (hasattr(origin, 'depth') and hasattr(magnitude, 'mag')):
                continue

            date = origin.time.datetime
            row = {
                'x': 1.0,
                'y': 1.0,
                'depth': origin.depth,
                'mag': magnitude.mag
            }
            yield (date, row)
