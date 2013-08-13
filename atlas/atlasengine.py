# -*- encoding: utf-8 -*-
"""
Top level module for ATLAS.

Contains the AtlasEngine class.

"""

from datamodel.eventstore import EventStore
from datamodel.seismiceventhistory import SeismicEventHistory
from datamodel.seismicevent import SeismicEvent


class AtlasEngine:
    """
    Top level class for ATLAS i.s.

    Instantiation this class bootstraps the entire application

    :ivar event_history: Provides the history of seismic events

    """

    def __init__(self):
        """
        Bootstraps and returns the Atlas engine

        The bootstrap process sets up a :class:`SeismicEventHistory` based
        on an in-memory sqlite database (for now).

        """
        store = EventStore(SeismicEvent, 'sqlite:///catalog.sqlite')
        self.event_history = SeismicEventHistory(store)

    def stop(self):
        self.event_history.store.close()