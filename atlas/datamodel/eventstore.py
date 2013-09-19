# -*- encoding: utf-8 -*-
"""
Defines the EventStore class which writes and reads event data from a database

"""

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from tools import PageCache
import base


DATE_ATTR_NAME = 'date_time'


class EventStore:
    """Manages access to the event store (database)

    The event store uses sqlalchemy to persist event objects to the
    database. As a consequence all objects that need to be persisted
    should inherit from the declarative base provided by :mod:`base`

    :ivar event_class: Class of the event objects that are to be stored
    :type event_class: Base

    """

    def __init__(self, event_class, store_url):
        """
        :param event_class: Class of the objects to be stored
        :type event_class: Base
        :param store_url: Database url

        """
        self._engine = create_engine(store_url, echo=False)
        base.Base.metadata.create_all(self._engine, checkfirst=True)
        Session = sessionmaker(bind=self._engine)
        self._session = Session()
        self._query = None
        self._page_cache = PageCache()
        self._num_events = 0
        self._event_class = event_class
        self.refresh()

    def purge(self):
        """Deletes all data from the catalog"""
        self._page_cache.invalidate()
        self._query = None
        base.Base.metadata.drop_all(bind=self._engine)
        base.Base.metadata.create_all(self._engine)

    def commit(self):
        """Commits pending changes to the store immediately"""
        self._session.commit()

    def write_event(self, event):
        """Write a new event to the store

        :param event: Event to write
        :type event: Base

        """
        self._session.add(event)
        self._page_cache.invalidate()
        self.commit()
        self.refresh()

    def write_events(self, events):
        """Write multiple events to the store

        :param events: List of events to write
        :type events: list

        """
        self._session.add_all(events)
        self._page_cache.invalidate()
        self.commit()
        self.refresh()

    def read_events(self, criteria):
        """Read and return all events from the store that meet the criteria provided by the caller

        :param criteria: List of logical criteria, e.g. (Event.data < a_date, Event.id > 10)
        :type criteria: list
        :rtype: list

        """
        if criteria is not None:
            results = self._query.filter(criteria)
        else:
            results = self._query.all()
        return results

    def latest_event(self):
        """Read and return the latest event from the store

        :rtype: Base

        """
        return self._query.first()

    def refresh(self):
        query = self._session.query(self._event_class).order_by(desc(DATE_ATTR_NAME))
        self._query = query
        self._page_cache.query = query
        self._num_events = query.count()

    def close(self):
        self._session.close()

    def __len__(self):
        return self._num_events

    def __getitem__(self, item):
        """Return the event at the specified index

        :param item: event index (0 being the newest)
        :type item: int
        :rtype: Base

        """
        return self._page_cache[item]