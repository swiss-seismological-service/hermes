# -*- encoding: utf-8 -*-
"""
ATLAS Core Application.

Top level object for the core Atlas application. Core meaning it is not
aware of any gui components (or other user control facilities). The user
control facilities should be hooked up in the Atlas class instead.

"""

import logging
from datetime import timedelta
from collections import namedtuple

from PyQt4 import QtCore

from forecastengine import ForecastEngine
from isha.common import RunInput
from model.store import Store
from model.atlasproject import AtlasProject
from model.datamodel import DataModel
from model.simulator import Simulator
from model.taskscheduler import TaskScheduler, ScheduledTask


# Used internally to pass information to repeating tasks
# t is the time when the task i launched, h_events and s_events is a list
# containing all seismic and hydraulic events that occurred before t
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

    def __init__(self, settings):
        """
        Bootstraps the Atlas core logic

        :param settings: object that holds the app settings
        :type settings: AppSettings

        """
        super(AtlasCore, self).__init__()
        self.settings = settings
        self.project = None

        # Initialize forecast engine
        engine = ForecastEngine()
        self.forecast_engine = engine

        # Initialize simulator
        self.simulator = Simulator(self._simulation_handler)

        # Time, state and other internals
        self._logger = logging.getLogger(__name__)
        #self._logger.setLevel(logging.DEBUG)
        self.state = CoreState.IDLE             # core state

        # Initialize scheduled tasks
        self._scheduler = TaskScheduler()
        # ...forecasting
        dt = self.settings.value('engine/fc_interval')
        forecast_task = ScheduledTask(self.run_forecast,
                                      timedelta(hours=dt),
                                      'Forecast')
        self._scheduler.add_task(forecast_task)
        self._forecast_task = forecast_task  # keep a reference for later
        # ...rate computations
        dt = self.settings.value('engine/rt_interval')
        rate_update_task = ScheduledTask(self.update_rates,
                                         timedelta(minutes=dt),
                                         'Rate update')
        self._scheduler.add_task(rate_update_task)

    @property
    def t_next_forecast(self):
        return self._forecast_task.run_time

    # Project handling

    def open_project(self, path):
        """
        Open ATLAS project file located at path

        :param path: path to the atlas project file
        :type path: str

        """
        # We add an additional / in front of the url. So now we have 3 slashes
        # in total, because host and db-name section are both empty for sqlite
        store_path = 'sqlite:///' + path
        store = Store(store_path, DataModel)
        self.project = AtlasProject(store)
        self.project.project_time_changed.connect(self._on_project_time_change)
        self.project_loaded.emit(self.project)
        self._logger.info('Opened project at ' + path)

    def close_project(self):
        self.project.close()
        self.project = None

    # Running

    def start(self):
        if self.settings.value('general/enable_lab_mode'):
            self.start_simulation()
        else:
            self._logger.notice('ATLAS only works in lab mode at the moment')

    def pause(self):
        if self.settings.value('general/enable_lab_mode'):
            self.pause_simulation()

    def stop(self):
        if self.settings.value('general/enable_lab_mode'):
            self.stop_simulation()

    # Simulation

    def start_simulation(self):
        """
        Starts the simulation.

        Replays the events from the seismic history.

        """
        if self.project is None:
            return
        self._logger.info('Starting simulation')
        # Reset task scheduler based on the first simulation step time
        time_range = self.project.event_time_range()
        self._scheduler.reset_schedule(time_range[0])
        # Configure simulator
        self.simulator.time_range = time_range
        infinite_speed = self.settings.value('lab_mode/infinite_speed')
        if infinite_speed:
            dt_h = self.settings.value('engine/fc_interval')
            dt = timedelta(hours=dt_h)
            step_signal = self.forecast_engine.forecast_complete
            self.simulator.step_on_external_signal(step_signal, dt)
        else:
            self.simulator.speed = self.settings.value('lab_mode/speed')
            self.simulator.step_on_internal_timer()
        # Start simulator
        self.simulator.start()
        # Set Core State to SIMULATING
        self.state = CoreState.SIMULATING
        self.state_changed.emit(self.state)

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
            # TODO: this is way too slow and doesn't belong here anyway
            # we should probably have 'Task' objects that get initialized
            # with a reference to the project (or whatever they need) and
            # which have a callback/signal
            self._logger.info('Scheduler has pending tasks. Gathering data.')
            h_events = self.project.hydraulic_history.events_after(t)
            s_events = self.project.seismic_history.events_before(t)
            info = RunInfo(t=t, h_events=h_events, s_events=s_events)
            self._logger.info('Run pending tasks')
            self._scheduler.run_pending_tasks(t, info)

    # Repeating tasks

    def run_forecast(self, info):
        dt_h = self.settings.value('engine/fc_bin_size')
        dt = timedelta(hours=dt_h)
        num_bins = self.settings.value('engine/num_fc_bins')
        fc_times = [info.t + i * dt for i in range(num_bins)]

        # Prepare model run input
        run_input = RunInput(info.t)
        run_input.seismic_events = info.s_events
        run_input.hydraulic_events = info.h_events
        run_input.forecast_times = fc_times
        # FIXME: the range should probably not be hardcoded
        run_input.forecast_mag_range = (0, 6)

        # Kick off the engine
        self.forecast_engine.run(run_input)

    def update_rates(self, info):
        data = [(e.date_time, e.magnitude) for e in info.s_events]
        if len(data) == 0:
            return

        t, m = zip(*data)
        t = list(t)
        m = list(m)
        rates = self.project.rate_history.compute_and_add(m, t, [info.t])
        self._logger.debug('New rate computed: ' + str(rates[0].rate))
