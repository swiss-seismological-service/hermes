# -*- encoding: utf-8 -*-
"""
History of hydraulic events, i.e changes in flow or pressure

"""

from eventhistory import EventHistory
from datetime import datetime, timedelta
from time import strptime, mktime
import csv

from hydraulicevent import HydraulicEvent


class HydraulicEventHistory(EventHistory):
    """
    Provides a history of hydraulic events and functions to read and write them
    from/to a persistent store. The class uses Qt signals to signal changes.

    """

    def __init__(self, store):
        super(HydraulicEventHistory, self).__init__(store, HydraulicEvent)

    def import_from_csv(self, path, date_format=None,
                        base_date=datetime(1970, 1, 1)):
        """
        Imports hydraulic events from a csv file

        The csv file must have a header row which identifies the following
        fields (any additional fields will be ignored):
            date: date string or time offset in days from base_date
                (if date_format is None)
            flow_dh: flow down hole [l/min]
            flow_xt: flow @ x-mas tree (top hole) [l/min]
            pr_dh: pressure down hole [bar]
            pr_xt: pressure @ x-mas tree (top hole) [bar]

        :param date_format: format string (see strptime()) for the date
            representation. If set to None, the import function will
            assume that it's fraction of days from base_date
        :param path: path to the csv file
        :type path: str
        :param base_date: the d_days number of days is added to the base date
            if date_format is None
        :type base_date: datetime

        """
        self.store.purge(self.entity)
        with open(path, 'rb') as csv_file:
            csv.register_dialect('hydr_data', delimiter=' ',
                                 skipinitialspace=True)
            reader = csv.DictReader(csv_file, dialect='hydr_data')
            events = []
            for entry in reader:
                if date_format is None:
                    dt = timedelta(days=float(entry['date']))
                    date_time = base_date + dt
                else:
                    time_struct = strptime(entry['date'], date_format)
                    date_time = datetime.fromtimestamp(mktime(time_struct))
                event = HydraulicEvent(date_time,
                                       flow_dh=float(entry['flow_dh']),
                                       flow_xt=float(entry['flow_xt']),
                                       pr_dh=float(entry['pr_dh']),
                                       pr_xt=float(entry['pr_xt']))
                events.append(event)
        self.store.add(events)
        self._emit_change_signal({})