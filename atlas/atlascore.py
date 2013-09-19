# -*- encoding: utf-8 -*-
"""
ATLAS Core Application.

Top level object for the core Atlas application. Core meaning it is not
aware of any gui components (or other user control facilities). The user
control facilities should be hooked up in the Atlas class instead.

"""

from datamodel.eventstore import EventStore
from datamodel.seismiceventhistory import SeismicEventHistory
from datamodel.seismicevent import SeismicEvent
from forecastengine import ForecastEngine
from simulator import Simulator


class AtlasCore:
    """
    Top level class for ATLAS i.s.

    Instantiation this class bootstraps the entire application

    :ivar event_history: Provides the history of seismic events

    """

    def __init__(self):
        """
        Bootstraps and controls the Atlas core logic

        The bootstrap process sets up a :class:`SeismicEventHistory` based
        on an in-memory sqlite database (for now).

        """
        store = EventStore(SeismicEvent, 'sqlite:///catalog.sqlite')
        self.event_history = SeismicEventHistory(store)
        self.forecast_engine = ForecastEngine()
        self.simulator = Simulator(self.event_history, self.simulation_handler)

    def replay_history(self, speed):
        """
        Replays the events from the seismic history

        :param speed: simulation speed (factor)

        """

    def compute_forecast(self, time):
        """
        Computes the forecast at time *time*

        """

    def quit(self):
        self.event_history.store.close()


    # Simulation
    def simulation_handler(simulation_time, event_occurred, simulation_ended):
        pass