# Atlas
#
# Abstract class that provides an auto-updating
# history of real world events. Events
# are read and written to/from an event store.
#
# Copyright (C) 2013 Lukas Heiniger

from datetime import datetime, timedelta
import csv

from eventhistory import EventHistory
from datamodel.seismicevent import SeismicEvent
from location import Location


class SeismicEventHistory(EventHistory):

    def get_events_between(self, start_date, end_date):
        criteria = (SeismicEvent.date_time >= start_date,
                    SeismicEvent.end_time <= end_date)
        events = self.store.read_events(criteria)
        return events

    def latest_event(self):
        event = self.store.latest_event()
        return event

    def __getitem__(self, item):
        event = self.store[item]
        return event

    def import_from_csv(self, path, base_date=datetime(1970,1,1)):
        """Imports seismic events from a csv file

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

    def __len__(self):
        return self.store.num_events()