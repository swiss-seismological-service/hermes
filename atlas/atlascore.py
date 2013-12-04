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
from model.atlasproject import AtlasProject
from model.datamodel import DataModel
from forecastengine import ForecastEngine
from model.simulator import Simulator
from datetime import timedelta
import logging


class CoreState:
    """ AtlasCore states """
    IDLE = 0
    PAUSED = 1
    SIMULATING = 2
    FORECASTING = 3


class CoreScheduler(object):
    """
    Manages the core internal schedule for forecasts and other recurring
    computations.

    """
    DEF_FC_INT = 6.0  # Default forecast interval in hours
    DEF_RT_INT = 1.0  # Default rate update interval in minutes

    def __init__(self):
        self.settings = QtCore.QSettings()
        self.t_forecast = None      # Time of next forecast
        self.t_rate_upd = None      # Time of next seismic rate update

    def start(self, t0):
        """
        Start the scheduler by scheduling the first computations based on t0.

        """
        self.t_forecast = t0
        self.t_rate_upd = t0
        self.schedule_next_forecast()
        self.schedule_next_rate_update()

    def reset(self):
        self.t_forecast = None
        self.t_rate_upd = None

    def schedule_next_forecast(self):
        """ Schedules the next forecast based on the previous one. """
        dt = self.settings.value('engine/fc_interval', self.DEF_FC_INT, float)
        self.t_forecast += timedelta(hours=dt)

    def schedule_next_rate_update(self):
        """ Schedules the next rate update based on the previous one. """
        dt = self.settings.value('engine/rt_interval', self.DEF_RT_INT, float)
        self.t_rate_upd += timedelta(minutes=dt)


class AtlasCore(QtCore.QObject):
    """
    Top level class for ATLAS i.s.

    Instantiation of this class bootstraps the entire application

    :ivar seismic_history: Provides the history of seismic events

    """

    # Signals
    state_changed = QtCore.pyqtSignal(int)
    project_loaded = QtCore.pyqtSignal(object)

    def __init__(self):
        """ Bootstraps the Atlas core logic """
        super(AtlasCore, self).__init__()
        self.settings = QtCore.QSettings()
        self.project = None

        # Initialize core components
        self.forecast_engine = ForecastEngine()
        self.simulator = Simulator(self._simulation_handler)

        # Time, state and other internals
        self._logger = logging.getLogger(__name__)
        self._scheduler = CoreScheduler()       # scheduler for computations
        self.state = CoreState.IDLE             # core state

    @property
    def t_next_forecast(self):
        return self._scheduler.t_forecast

    # Project handling

    def open_project(self, path):
        store_path = 'sqlite://' + path
        store = Store(store_path, DataModel)
        self.project = AtlasProject(store)
        self.project.project_time_changed.connect(self._on_project_time_change)
        self.project_loaded.emit(self.project)
        self._logger.info('Opened project at ' + path)

    def close_project(self):
        self.project.close()
        self.project = None

    # Simulation

    def start_simulation(self):
        """
        Starts the simulation.

        Replays the events from the seismic history.

        """
        if self.project is None:
            return

        self.simulator.time_range = self.project.event_time_range()
        self.simulator.start()
        self._scheduler.start(self.simulator.simulation_time)
        self.state = CoreState.SIMULATING
        self.state_changed.emit(self.state)
        self._logger.info('Starting simulation')

    def pause_simulation(self):
        """ Pauses the simulation. """
        self.simulator.pause()
        self.state = CoreState.PAUSED
        self.state_changed.emit(self.state)

    def stop_simulation(self):
        """ Stops the simulation """
        self.simulator.stop()
        self._scheduler.reset()
        self.state = CoreState.IDLE
        self.state_changed.emit(self.state)
        self._logger.info('Stopping simulation')

    # Simulation handling

    def _simulation_handler(self, simulation_time):
        """ Invoked by the simulation whenever the project time changes """
        self.project.update_project_time(simulation_time)

    # Project time updates

    def _on_project_time_change(self, t):
        """
        Invoked when the project time changes. Triggers computations at fixed
        intervals.

        """

        # Project time changes can also occur on startup or due to manual user
        # interaction. In those cases we don't trigger any computations.
        forecast_states = [CoreState.SIMULATING, CoreState.FORECASTING]
        if self.state not in forecast_states:
            return

        # Run forecasts
        t_fc = self._scheduler.t_forecast
        if t > t_fc:
            self._scheduler.schedule_next_forecast()
            h_events = self.project.hydraulic_history.events_before(t_fc)
            s_events = self.project.seismic_history.events_before(t_fc)
            self.forecast_engine.run(h_events, s_events, t_fc)

        # Compute new rates
        t_rt = self._scheduler.t_rate_upd
        if t > t_rt:
            self._scheduler.schedule_next_rate_update()
            self._logger.debug('Computing rates')