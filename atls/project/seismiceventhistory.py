# -*- encoding: utf-8 -*-
"""
History of seismic events

"""

from eventhistory import EventHistory
from eventimporter import EventImporter
from domainmodel.seismicevent import SeismicEvent
from geometry import Point
import logging
import traceback


class SeismicEventHistory(EventHistory):
    """
    Provides a history of seismic events and functions to read and write them
    from/to a persistent store. The class uses Qt signals to signal changes.

    """

    def __init__(self, store):
        super(SeismicEventHistory, self).__init__(store, SeismicEvent)
        self._logger = logging.getLogger(__name__)

    def import_events(self, importer):
        """
        Imports seismic events from a csv file by using an EventImporter

        The EventReporter must return the following fields (which must thus
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
            self._logger.error('Failed to import events. Make sure the .csv '
                               'file contains x, y, depth, and mag fields '
                               'and that the date field has the format '
                               'dd.mm.yyyyTHH:MM:SS. The original error was '
                               + traceback.format_exc())
        else:
            self.store.purge(self.entity)
            self.store.add(events)
            self._logger.info('Imported {} events.'.format(len(events)))
            self.reload_from_store()
            self._emit_change_signal({})