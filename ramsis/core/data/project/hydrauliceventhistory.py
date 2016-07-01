# -*- encoding: utf-8 -*-
"""
History of hydraulic events, i.e changes in flow or pressure

"""

import logging
import traceback

from core.data.project.eventhistory import EventHistory
from core.data.hydraulicevent import HydraulicEvent


class HydraulicEventHistory(EventHistory):
    """
    Provides a history of hydraulic events and functions to read and write them
    from/to a persistent store. The class uses Qt signals to signal changes.

    """

    def __init__(self, store):
        EventHistory.__init__(self, store, HydraulicEvent)
        self._logger = logging.getLogger(__name__)

    def import_events(self, importer, timerange=None):
        """
        Imports seismic events from a csv file by using an EventReporter

        The EventReporter must return the following fields (which must thus
        be present in the csv file)

        - ``flow_dh``: flow down hole [l/min]
        - ``flow_xt``: flow @ x-mas tree (top hole) [l/min]
        - ``pr_dh``: pressure down hole [bar]
        - ``pr_xt``: pressure @ x-mas tree (top hole) [bar]

        :param importer: an EventReporter object
        :type importer: EventImporter

        """
        events = []
        try:
            for date, fields in importer:
                event = HydraulicEvent(date,
                                       flow_dh=float(
                                           fields.get('flow_dh') or 0),
                                       flow_xt=float(
                                           fields.get('flow_xt') or 0),
                                       pr_dh=float(fields.get('pr_dh') or 0),
                                       pr_xt=float(fields.get('pr_xt') or 0))
                events.append(event)
        except:
            self._logger.error('Failed to import hydraulic events. Make sure '
                               'the .csv file contains top and bottom hole '
                               'flow and pressure fields and that the date '
                               'field has the format dd.mm.yyyyTHH:MM:SS. The '
                               'original error was ' +
                               traceback.format_exc())
        else:
            predicate = None
            if timerange:
                predicate = (self.entity.date_time >= timerange[0],
                             self.entity.date_time <= timerange[1])
            self.store.purge_entity(self.entity, predicate)
            self.store.add(events)
            self._logger.info('Imported {} hydraulic events.'.format(
                len(events)))
            self.reload_from_store()
            self._emit_change_signal({})
