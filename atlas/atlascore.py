# -*- encoding: utf-8 -*-
"""
ATLAS Core Application.

Top level object for the core Atlas application. Core meaning it is not
aware of any gui components (or other user control facilities). The user
control facilities should be hooked up in the Atlas class instead.

"""

from PyQt4 import QtCore

from model.store import Store
from model.atlasproject import AtlasProject
from model.datamodel import DataModel
from forecastengine import ForecastEngine
from model.simulator import Simulator
from model.taskscheduler import TaskScheduler, ScheduledTask
from collections import namedtuple
import logging


# Used internally to pass information to repeating tasks
RunInfo = namedtuple('RunInfo', 't, h_events, s_events')


class CoreState:
    """ AtlasCore states """
    IDLE = 0
    PAUSED = 1
    SIMULATING = 2
    FORECASTING = 3


class AtlasCore(QtCore.QObject):
    """
    Top level class for ATLAS i.s.

    Instantiation of this class bootstraps the entire application

    :ivar seismic_history: Provides the history of seismic events

    """

    # Signals
    state_changed = QtCore.pyqtSignal(int)
    project_loaded = QtCore.pyqtSignal(object)

    DEF_FC_INT = 6  # default forecast interval is 6 hours
    DEF_RT_INT = 1  # default rate computation interval is 1 minute

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
        self.state = CoreState.IDLE             # core state

        # Initialize scheduled tasks
        self._scheduler = TaskScheduler()
        # ...forecasting
        dt = self.settings.value('engine/fc_interval', self.DEF_FC_INT, float)
        forecast_task = ScheduledTask(self.run_forecast, dt, 'Forecast')
        self._scheduler.add_task(forecast_task)
        self._forecast_task = forecast_task  # keep a reference for later
        # ...rate computations
        dt = self.settings.value('engine/rt_interval', self.DEF_RT_INT, float)
        rate_update_task = ScheduledTask(self.update_rates, dt, 'Rate update')
        self._scheduler.add_task(rate_update_task)

    @property
    def t_next_forecast(self):
        return self._forecast_task.run_time

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
        self._scheduler.reset_schedule(self.simulator.simulation_time)
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

        if self._scheduler.has_pending_tasks(t):
            h_events = self.project.hydraulic_history.events_before(t)
            s_events = self.project.seismic_history.events_before(t)
            info = RunInfo(t=t, h_events=h_events, s_events=s_events)
            self._scheduler.run_pending_tasks(t, info)

    # Repeating tasks

    def run_forecast(self, info):
        self.forecast_engine.run(info.h_events, info.s_events, info.t)

    def update_rates(self, info):
        pass