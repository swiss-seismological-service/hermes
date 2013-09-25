# -*- encoding: utf-8 -*-
"""
History of seismic events

"""

from datetime import datetime, timedelta
import csv

from datamodel.seismicevent import SeismicEvent
from location import Location
from PyQt4 import QtCore


class SeismicEventHistory(QtCore.QObject):
    """
    Provides a history of seismic events and functions to read and write them
    from/to a persistent store. The class uses Qt signals to signal changes.

    :ivar store: event store (interface to persistent store / db)
    :ivar history_changed: Qt signal, emitted when the history changes

    """

    history_changed = QtCore.pyqtSignal(dict)

    def __init__(self, store):
        super(SeismicEventHistory, self).__init__()
        self.store = store

    def get_events_between(self, start_date, end_date):
        criteria = (SeismicEvent.date_time >= start_date,
                    SeismicEvent.end_time <= end_date)
        events = self.store.read_events(criteria)
        return events


    def latest_event(self, time=None):
        if time is None:
            event = self.store.latest_event()
        else:
            criteria = (SeismicEvent.date_time < time)
            event = self.store.read_last(criteria)
        return event


    def __getitem__(self, item):
        event = self.store[item]
        return event


    def __len__(self):
        return len(self.store)


    def import_from_csv(self, path, base_date=datetime(1970,1,1)):
        """
        Imports seismic events from a csv file

        The csv file must have a header row which identifies the following
        fields: seq_no: sequence number
                d_days: time offset in days
                lat: latitude
                lon: longitude
                mag: magnitude

        :param path: path to the csv file
        :type path: str
        :param base_date: the d_days number of days is added to the base date
        :type base_date: datetime

        """
        self.store.purge()
        with open(path, 'rb') as csv_file:
            csv.register_dialect('magcat', delimiter=' ', skipinitialspace=True)
            reader = csv.DictReader(csv_file, dialect='magcat')
            events = []
            for entry in reader:
                location = Location(float(entry['lon']), float(entry['lat']))
                dt = timedelta(days=float(entry['d_days']))
                date_time = base_date + dt
                event = SeismicEvent(date_time, float(entry['mag']), location)
                events.append(event)
        self.store.write_events(events)
        self.history_changed.emit({})