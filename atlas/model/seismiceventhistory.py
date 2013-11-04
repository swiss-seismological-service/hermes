# -*- encoding: utf-8 -*-
"""
History of seismic events

"""

from eventhistory import EventHistory
from datetime import datetime, timedelta
from time import mktime, strptime
import csv

from seismicevent import SeismicEvent
from location import Location
from PyQt4 import QtCore


class SeismicEventHistory(EventHistory):
    """
    Provides a history of seismic events and functions to read and write them
    from/to a persistent store. The class uses Qt signals to signal changes.

    """

    def __init__(self, store):
        super(SeismicEventHistory, self).__init__(store, SeismicEvent)

    def import_from_csv(self, path, date_format=None,
                        base_date=datetime(1970, 1, 1)):
        """
        Imports seismic events from a csv file

        The csv file must have a header row which identifies the following
        fields (any additional fields will be ignored):
            date: date string or time offset in days from base_date
                (if date_format is None)
            lat: latitude
            lon: longitude
            mag: magnitude
        :param date_format: format string (see strptime()) for the date
            representation. If set to None, the import function will
            assume that it's fraction of days from base_date
        :param path: path to the csv file
        :type path: str
        :param base_date: the d_days number of days is added to the base date
        :type base_date: datetime

        """
        self.store.purge(self.entity)
        with open(path, 'rb') as csv_file:
            csv.register_dialect('magcat', delimiter=' ', skipinitialspace=True)
            reader = csv.DictReader(csv_file, dialect='magcat')
            events = []
            for entry in reader:
                location = Location(float(entry['lon']), float(entry['lat']))
                if date_format is None:
                    dt = timedelta(days=float(entry['date']))
                    date_time = base_date + dt
                else:
                    time_struct = strptime(entry['date'], date_format)
                    date_time = datetime.fromtimestamp(mktime(time_struct))
                event = SeismicEvent(date_time, float(entry['mag']), location)
                events.append(event)
        self.store.add(events)
        self._emit_change_signal({})