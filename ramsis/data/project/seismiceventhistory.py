# -*- encoding: utf-8 -*-
"""
History of seismic events

"""

import logging
import traceback

from data.project.eventhistory import EventHistory
from data.seismicevent import SeismicEvent
from data.geometry import Point


class SeismicEventHistory(EventHistory):
    """
    Provides a history of seismic events and functions to read and write them
    from/to a persistent store. The class uses Qt signals to signal changes.

    """

    def __init__(self, store):
        EventHistory.__init__(self, store, SeismicEvent)
        self._logger = logging.getLogger(__name__)

    def import_events(self, importer, timerange=None):
        """
        Imports seismic events from a csv file by using an EventImporter

        The EventImporter must return the following fields (which must thus
        be present in the csv file)
            x: x coordinate [m]
            y: y coordinate [m]
            depth: depth [m], positive downwards
            mag: magnitude
        :param importer: an EventImporter object
        :type importer: EventImporter

        """
        events = []
        try:
            for date, fields in importer:
                location = Point(float(fields['x']),
                                 float(fields['y']),
                                 float(fields['depth']))
                event = SeismicEvent(date, float(fields['mag']), location)
                events.append(event)
        except:
            self._logger.error('Failed to import seismic events. Make sure '
                               'the .csv file contains x, y, depth, and mag '
                               'fields and that the date field has the format '
                               'dd.mm.yyyyTHH:MM:SS. The original error was ' +
                               traceback.format_exc())
        else:
            predicate = None
            if timerange:
                predicate = (self.entity.date_time >= timerange[0],
                             self.entity.date_time <= timerange[1])
            self.store.purge_entity(self.entity, predicate)
            self.store.add(events)
            self._logger.info('Imported {} seismic events.'.format(
                len(events)))
            self.reload_from_store()
            self._emit_change_signal({})

    def events_before(self, end_date, mc=0):
        """ Returns all events >mc before and including *end_date* """
        return [e for e in self._events
                if e.date_time < end_date and e.magnitude > mc]
