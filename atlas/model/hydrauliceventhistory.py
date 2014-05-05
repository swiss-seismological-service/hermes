# -*- encoding: utf-8 -*-
"""
History of hydraulic events, i.e changes in flow or pressure

"""

from eventhistory import EventHistory
from eventimporter import EventImporter
from hydraulicevent import HydraulicEvent


class HydraulicEventHistory(EventHistory):
    """
    Provides a history of hydraulic events and functions to read and write them
    from/to a persistent store. The class uses Qt signals to signal changes.

    """

    def __init__(self, store):
        super(HydraulicEventHistory, self).__init__(store, HydraulicEvent)

    def import_events(self, importer):
        """
        Imports seismic events from a csv file by using an EventReporter

        The EventReporter must return the following fields (which must thus
        be present in the csv file)
            flow_dh: flow down hole [l/min]
            flow_xt: flow @ x-mas tree (top hole) [l/min]
            pr_dh: pressure down hole [bar]
            pr_xt: pressure @ x-mas tree (top hole) [bar]

        :param importer: an EventReporter object
        :type importer: EventImporter

        """
        self.store.purge(self.entity)
        events = []
        for date, fields in importer:
            event = HydraulicEvent(date,
                                   flow_dh=float(fields.get('flow_dh') or 0),
                                   flow_xt=float(fields.get('flow_xt') or 0),
                                   pr_dh=float(fields.get('pr_dh') or 0),
                                   pr_xt=float(fields.get('pr_xt') or 0))
            events.append(event)

        self.store.add(events)
        self.reload_from_store()
        self._emit_change_signal({})