# -*- encoding: utf-8 -*-
"""
History of  events

"""

from datetime import datetime, timedelta
import csv

from PyQt4 import QtCore

DATE_TIME_ATTR_NAME = 'date_time'

class EventHistory(QtCore.QObject):
    """
    Provides a history of  events and functions to read and write them
    from/to a persistent store. The class uses Qt signals to signal changes.

    :ivar store: event store (interface to persistent store / db)

    """

    history_changed = QtCore.pyqtSignal(dict)
    """
    history_changed is a Qt signal, emitted when the history changes. The
    signal carries a dict with further information about the changes
    contained as follows:
        'history': the history object that has changed

    Subclasses may add additional fields

    """

    def __init__(self, store, entity):
        """
        Creates and initializes an event history

        :param store: the store the history can use to persist events
        :type store: EventStore
        :param entity: the class that represents events in this history. An
        event class must have a date_time attribute that stores the
        datetime of the event.

        """
        super(EventHistory, self).__init__()
        store.init_sequential_read_cache(entity, DATE_TIME_ATTR_NAME)
        self.store = store
        self.entity = entity

    def get_events_between(self, start_date, end_date):
        predicate = (self.entity.date_time >= start_date,
                     self.entity.date_time <= end_date)
        events = self.store.read_all(self.entity, predicate)
        return events

    def latest_event(self, time=None):
        """
        Returns the latest event before time *time*

        If not time constraint is given, the latest event in the entire history
        is returned.

        :param time: time constraint for latest event
        :type time: datetime

        """
        if time is None:
            event = self.store.read_last(self.entity)
        else:
            predicate = (self.entity.date_time < time)
            event = self.store.read_last(self.entity, predicate)
        return event

    def __getitem__(self, item):
        event = self.store.read(self.entity, item)
        return event

    def __len__(self):
        return self.store.count(self.entity)

    def _emit_change_signal(self, change_dict):
        default_dict = {'history': self}
        d = dict(default_dict.items() + change_dict.items())
        self.history_changed.emit(d)
