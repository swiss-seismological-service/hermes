# -*- encoding: utf-8 -*-
"""
Defines an abstract base class for objects that provide a history of events

"""

import abc


class EventHistory:
    """Abstract base class for objects that provide a history of events

    An event history object must be instantiated with a store object
    which provides access to the database where events are stored

    :ivar store: event store (interface to persistent store / db)
    :type store: EventStore

    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, store):
        """
        :param store: The event store to be used by the history
        :type store: EventStore

        """
        self.store = store

    @abc.abstractmethod
    def get_events_between(self, start_date, end_date):
        """ Returns all events that occurred between a given start and end date

        :param start_date: start date of the history to return
        :type start_date: datetime
        :param end_date: end date of the history to return
        :type end_date: datetime
        :rtype: list

        """
        return

    @abc.abstractmethod
    def latest_event(self):
        """Returns the latest event in the event history"""
        return
