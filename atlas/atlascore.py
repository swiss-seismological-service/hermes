# -*- encoding: utf-8 -*-
"""
ATLAS Core Application.

Top level object for the core Atlas application. Core meaning it is not
aware of any gui components (or other user control facilities). The user
control facilities should be hooked up in the Atlas class instead.

"""

from datetime import datetime

from PyQt4 import QtCore

from model.store import Store
from model.seismiceventhistory import SeismicEventHistory
from model.hydrauliceventhistory import HydraulicEventHistory
from model.datamodel import DataModel
from forecastengine import ForecastEngine
from model.simulator import Simulator
from datetime import timedelta

from tools import Profiler

class CoreState:
    IDLE = 0
    PAUSED = 1
    SIMULATING = 2
    FORECASTING = 3

class AtlasCore(QtCore.QObject):
    """
    Top level class for ATLAS i.s.

    Instantiation this class bootstraps the entire application

    :ivar seismic_history: Provides the history of seismic events

    """

    # Signals
    state_changed = QtCore.pyqtSignal(int)
    project_time_changed = QtCore.pyqtSignal(datetime)

    def __init__(self):
        """
        Bootstraps and controls the Atlas core logic

        The bootstrap process sets up a :class:`SeismicEventHistory` based
        on an in-memory sqlite database (for now).

        """
        super(AtlasCore, self).__init__()
        store = Store('sqlite:///data.sqlite', DataModel)
        self.settings = QtCore.QSettings()

        # Initialize core components
        self.seismic_history = SeismicEventHistory(store)
        self.hydraulic_history = HydraulicEventHistory(store)
        self.forecast_engine = ForecastEngine()
        self.simulator = Simulator(self.seismic_history,
                                   self._simulation_handler)

        # Time and state
        self._project_time = datetime.now()     # current time in the project
        self._t_forecast = None                 # time of next forecast
        self.state = CoreState.IDLE        # core state


    @property
    def project_time(self):
        return self._project_time

    def start(self):
        es = self.seismic_history[0]
        eh = self.hydraulic_history[0]

        if es is None and eh is None:
            t0 = datetime.now()
        elif es is None:
            t0 = eh.date_time
        elif eh is None:
            t0 = es.date_time
        else:
            t0 = eh.date_time if eh.date_time < es.date_time else es.date_time

        self._update_project_time(t0)



    # Simulation

    def start_simulation(self):
        """
        Replays the events from the seismic history

        """
        dt = self.settings.value('engine/fc_interval', 6, float)
        self.simulator.start()
        self._t_forecast = self.simulator.simulation_time + timedelta(hours=dt)
        self.state = CoreState.SIMULATING
        self.state_changed.emit(self.state)

    def pause_simulation(self):
        self.simulator.pause()
        self.state = CoreState.PAUSED
        self.state_changed.emit(self.state)

    def stop_simulation(self):
        self.simulator.stop()
        self.state = CoreState.IDLE
        self.state_changed.emit(self.state)

    def compute_forecast(self, time):
        """
        Computes the forecast at time *time*

        """
        pass

    def quit(self):
        self.seismic_history.store.close()


    # Simulation

    def _simulation_handler(self, simulation_time, num_events, ended):
        self._update_project_time(simulation_time)

    # Project time updates

    def _update_project_time(self, t):
        """
        Updates the project time to the time *t*, emits the project time change
        signal and starts a new forecast if needed

        """
        self._project_time = t
        self.project_time_changed.emit(t)

        forecast_states = [CoreState.SIMULATING, CoreState.FORECASTING]
        if self.state in forecast_states and t > self._t_forecast:
            dt = self.settings.value('engine/fc_interval', 6, float)
            self._t_forecast += timedelta(hours=dt)

            h_events = self.hydraulic_history.events_before(self._t_forecast)
            s_events = self.seismic_history.events_before(self._t_forecast)

            self.forecast_engine.run(h_events, s_events, self._t_forecast)