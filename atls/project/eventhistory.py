# -*- encoding: utf-8 -*-
"""
History of  events

"""

from datetime import datetime

from PyQt4 import QtCore

DATE_TIME_ATTR_NAME = 'date_time'


class EventHistory(QtCore.QObject):
    """
    Provides a history of events and functions to read and write them
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
        self.store = store
        self.entity = entity
        self._events = []

    def reload_from_store(self):
        """
        Reloads all events from the persistent store.

        """
        self._events = self.store.read_all(self.entity, order='date_time')

    def clear(self):
        """
        Delete all data from the db

        """
        self.store.purge(self.entity)
        self._events = []
        self._emit_change_signal({})

    def all_events(self):
        return self._events

    def events_between(self, start_date, end_date):
        """
        Returns all events between and including *start_date* and *end_date*.

        """
        return [e for e in self._events if start_date < e.date_time < end_date]

    def events_before(self, end_date):
        """ Returns all events before and including *end_date* """
        return [e for e in self._events if e.date_time < end_date]

    def events_after(self, start_date):
        """ Returns all events after and including *start_date* """
        return [e for e in self._events if start_date < e.date_time]

    def latest_event(self, time=None):
        """
        Returns the latest event before time *time*

        If not time constraint is given, the latest event in the entire history
        is returned.

        :param time: time constraint for latest event
        :type time: datetime

        """
        if time is None:
            events = self._events
        else:
            events = self.events_before(time)
        return events[-1] if len(events) > 0 else None

    def add(self, ev):
        """
        Add one or more events to the history (and store)

        :param ev: event or list of events

        """
        try:
            ev_list = [e for e in ev]
        except TypeError:
            ev_list = [ev]
        self._events += ev_list
        self.store.add(ev_list)
        self._emit_change_signal({})

    def __getitem__(self, item):
        return self._events[item]

    def __len__(self):
        return len(self._events)

    def _emit_change_signal(self, change_dict):
        default_dict = {'history': self}
        d = dict(default_dict.items() + change_dict.items())
        self.history_changed.emit(d)
