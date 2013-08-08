# -*- encoding: utf-8 -*-
"""
Defines the EventStore class which writes and reads event data from a database

"""

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

import base


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
        engine = create_engine(store_url, echo=False)
        base.Base.metadata.create_all(engine, checkfirst=True)
        Session = sessionmaker(bind=engine)
        self._session = Session()
        self.event_class = event_class

    def commit(self):
        """Commits pending changes to the store immediately"""
        self._session.commit()

    def write_event(self, event):
        """Write a new event to the store

        :param event: Event to write
        :type event: Base

        """
        self._session.add(event)

    def write_events(self, events):
        """Write multiple events to the store

        :param events: List of events to write
        :type events: list

        """
        self._session.add_all(events)

    def read_events(self, criteria):
        """Read and return all events from the store that meet the criteria provided by the caller

        :param criteria: List of logical criteria, e.g. (Event.data < a_date, Event.id > 10)
        :type criteria: list
        :rtype: list

        """
        if criteria is not None:
            results = self._session.query().filter(criteria)
        else:
            results = self._session.query().all()
        return results

    def latest_event(self, date_attr_name='date_time'):
        """Read and return the latest event from the store

        :param date_attr_name: Name of the event attribute that contains the date
        :type date_attr_name: str
        :rtype: Base

        """
        return self._session.query(self.event_class).order_by(desc(date_attr_name)).first()