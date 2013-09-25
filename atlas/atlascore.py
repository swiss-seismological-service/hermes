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
from datetime import datetime
from PyQt4 import QtCore

class AtlasCoreState:
    IDLE = 0
    PAUSED = 1
    SIMULATING = 2
    FORECASTING = 3

class AtlasCore(QtCore.QObject):
    """
    Top level class for ATLAS i.s.

    Instantiation this class bootstraps the entire application

    :ivar event_history: Provides the history of seismic events

    """

    # Signals
    state_changed = QtCore.pyqtSignal(int)

    def __init__(self):
        """
        Bootstraps and controls the Atlas core logic

        The bootstrap process sets up a :class:`SeismicEventHistory` based
        on an in-memory sqlite database (for now).

        """
        super(AtlasCore, self).__init__()
        store = EventStore(SeismicEvent, 'sqlite:///catalog.sqlite')
        self.event_history = SeismicEventHistory(store)
        self.forecast_engine = ForecastEngine()
        self.simulator = Simulator(self.event_history, self.simulation_handler)
        self.project_time = datetime.now()
        self.state = AtlasCoreState.IDLE


    # Simulation

    def start_simulation(self):
        """
        Replays the events from the seismic history

        :param speed: simulation speed (factor)

        """
        self.simulator.start()
        self.state = AtlasCoreState.SIMULATING
        self.state_changed.emit(self.state)

    def pause_simulation(self):
        self.simulator.pause()
        self.state = AtlasCoreState.PAUSED
        self.state_changed.emit(self.state)

    def stop_simulation(self):
        self.simulator.stop()
        self.state = AtlasCoreState.IDLE
        self.state_changed.emit(self.state)

    def compute_forecast(self, time):
        """
        Computes the forecast at time *time*

        """

    def quit(self):
        self.event_history.store.close()


    # Simulation

    def simulation_handler(self, simulation_time, event_occurred, simulation_ended):
        self.project_time = simulation_time
        if event_occurred:
            change_dict = {'simulation_time': simulation_time}
            self.event_history.history_changed.emit(change_dict)