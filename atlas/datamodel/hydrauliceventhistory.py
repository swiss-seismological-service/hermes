# -*- encoding: utf-8 -*-
"""
History of hydraulic events, i.e changes in flow or pressure

"""

from eventhistory import EventHistory
from datetime import datetime, timedelta
import csv

from datamodel.hydraulicevent import HydraulicEvent, HydraulicEventData
from location import Location
from PyQt4 import QtCore


class HydraulicEventHistory(EventHistory):
    """
    Provides a history of hydraulic events and functions to read and write them
    from/to a persistent store. The class uses Qt signals to signal changes.

    """

    def __init__(self, store):
        super(EventHistory, self).__init__(store, HydraulicEvent)

    def import_from_csv(self, path, base_date=datetime(1970, 1, 1)):
        """
        Imports hydraulic events from a csv file

        The csv file must have a header row which identifies the following
        fields: d_days: time offset in days
                flow_dh: ?
                flow_xt: ?
                pr_dh: ?
                pr_xt: ?
                flow_in: ?
                const: ?

        :param path: path to the csv file
        :type path: str
        :param base_date: the d_days number of days is added to the base date
        :type base_date: datetime

        """
        self.store.purge(self.entity)
        with open(path, 'rb') as csv_file:
            csv.register_dialect('hydr_data', delimiter=' ', skipinitialspace=True)
            reader = csv.DictReader(csv_file, dialect='hydr_data')
            events = []
            for entry in reader:
                dt = timedelta(days=float(entry['d_days']))
                date_time = base_date + dt
                data = HydraulicEventData(
                    flow_dh=entry['flow_dh'],
                    flow_xt=entry['flow_xt'],
                    flow_in=entry['flow_in'],
                    pressure_dh=entry['pressure_dh'],
                    pressure_xt=entry['pressure_xt'],
                    flow_in=entry['flow_in'],
                    const=entry['const'],
                )
                event = HydraulicEvent(date_time, data)
                events.append(event)
        self.store.add(events)
        self._emit_change_signal({})