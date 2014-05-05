# -*- encoding: utf-8 -*-
"""
History of seismic events

"""

from eventhistory import EventHistory
from eventimporter import EventImporter
from seismicevent import SeismicEvent
from location import Location


class SeismicEventHistory(EventHistory):
    """
    Provides a history of seismic events and functions to read and write them
    from/to a persistent store. The class uses Qt signals to signal changes.

    """

    def __init__(self, store):
        super(SeismicEventHistory, self).__init__(store, SeismicEvent)

    def import_events(self, importer):
        """
        Imports seismic events from a csv file by using an EventReporter

        The EventReporter must return the following fields (which must thus
        be present in the csv file)
            lat: latitude
            lon: longitude
            mag: magnitude
        :param importer: an EventImporter object
        :type importer: EventImporter

        """
        self.store.purge(self.entity)

        events = []
        for date, fields in importer:
            location = Location(float(fields['lon']), float(fields['lat']))
            event = SeismicEvent(date, float(fields['mag']), location)
            events.append(event)
        self.store.add(events)
        self.reload_from_store()
        self._emit_change_signal({})