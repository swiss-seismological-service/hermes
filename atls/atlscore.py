# -*- encoding: utf-8 -*-
"""
ATLS Core Application.

Top level object for the core Atls application. Core meaning it is not
aware of any gui components (or other user control facilities). The user
control facilities should be hooked up in the Atls class instead.

"""

import logging
from datetime import timedelta
from collections import namedtuple

from PyQt4 import QtCore

from forecastengine import ForecastEngine
from isha.common import ModelInput
from project.store import Store
from project.atlsproject import AtlsProject
from domainmodel.datamodel import DataModel
from simulator import Simulator
from taskscheduler import TaskScheduler, ScheduledTask

import os
#from tools import Profiler




# Used internally to pass information to repeating tasks
# t_project is the project time at which the task is launched
TaskRunInfo = namedtuple('TaskRunInfo', 't_project')


class CoreState:
    """ AtlsCore states """
    IDLE = 0
    PAUSED = 1
    SIMULATING = 2
    FORECASTING = 3


class AtlsCore(QtCore.QObject):
    """
    Top level class for ATLS i.s.

    Instantiation of this class bootstraps the entire application

    :ivar seismic_history: Provides the history of seismic events
    :ivar project: Atls Project
    :type project: AtlsProject

    """

    # Signals
    state_changed = QtCore.pyqtSignal(int)
    project_loaded = QtCore.pyqtSignal(object)

    def __init__(self, settings):
        """
        Bootstraps the Atls core logic

        :param settings: object that holds the app settings
        :type settings: AppSettings

        """
        super(AtlsCore, self).__init__()
        self.settings = settings
        self.project = None
        self._forecast_task = None

        # Initialize forecast engine
        engine = ForecastEngine(settings.value('ISHA/models'))
        self.forecast_engine = engine

        # Initialize simulator
        self.simulator = Simulator(self._simulation_handler)

        # Time, state and other internals
        self._logger = logging.getLogger(__name__)
        #self._logger.setLevel(logging.DEBUG)
        self.state = CoreState.IDLE             # core state

        # Initialize scheduled tasks
        self._scheduler = self._create_task_scheduler()

    @property
    def t_next_forecast(self):
        return self._forecast_task.run_time

    def _create_task_scheduler(self):
        """
        Creates the task scheduler and schedules recurring tasks

        """
        scheduler = TaskScheduler()

        # Forecasting Task
        dt = self.settings.value('engine/fc_interval', type=float)
        forecast_task = ScheduledTask(task_function=self.run_forecast,
                                      dt=timedelta(hours=dt),
                                      name='Forecast')
        scheduler.add_task(forecast_task)
        self._forecast_task = forecast_task  # keep a reference for later

        # Rate computations
        dt = self.settings.value('engine/rt_interval', type=float)
        rate_update_task = ScheduledTask(task_function=self.update_rates,
                                         dt=timedelta(minutes=dt),
                                         name='Rate update')
        scheduler.add_task(rate_update_task)

        return scheduler

    # Project handling

    def open_project(self, path):
        """
        Open ATLS project file located at path

        :param path: path to the atls project file
        :type path: str

        """
        if not os.path.exists(path):
            self._logger.error('Could not find project: ' + path)
            return
        # We add an additional / in front of the url. So now we have 3 slashes
        # in total, because host and db-name section are both empty for sqlite
        store_path = 'sqlite:///' + path
        self._logger.info('Loading project at ' + path +
                          ' - This might take a while...')
        store = Store(store_path, DataModel)
        self.project = AtlsProject(store)
        self.project.project_time_changed.connect(self._on_project_time_change)
        self.project_loaded.emit(self.project)
        self._logger.info('...done')

    def close_project(self):
        self.project.close()
        self.project = None

    # Running

    def start(self):
        if self.settings.value('enable_lab_mode'):
            self.start_simulation()
        else:
            self._logger.notice('ATLS only works in lab mode at the moment')

    def pause(self):
        if self.settings.value('/enable_lab_mode'):
            self.pause_simulation()

    def stop(self):
        if self.settings.value('enable_lab_mode'):
            self.stop_simulation()

    # Simulation

    def start_simulation(self):
        """
        Starts the simulation.

        Replays the events from the seismic history.

        """
        #self._profiler = Profiler()
        #self._profiler.start()
        self._num_runs = 0
        if self.project is None:
            return
        self._logger.info('Starting simulation')
        # Reset task scheduler based on the first simulation step time
        time_range = self.project.event_time_range()
        self._scheduler.reset_schedule(time_range[0])
        # Configure simulator
        self.simulator.time_range = time_range
        infinite_speed = self.settings.value('lab_mode/infinite_speed',
                                             type=bool)
        if infinite_speed:
            dt_h = self.settings.value('engine/fc_interval', type=float)
            dt = timedelta(hours=dt_h)
            step_signal = self.forecast_engine.forecast_complete
            self.simulator.step_on_external_signal(step_signal, dt)
        else:
            self.simulator.speed = self.settings.value('lab_mode/speed',
                                                       type=float)
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

    def _on_project_time_change(self, t_project):
        """
        Invoked when the project time changes. Triggers scheduled computations.

        :param t_project: current project time
        :type t_project: datetime

        """
        # Project time changes can also occur on startup or due to manual user
        # interaction. In those cases we don't trigger any computations.
        forecast_states = [CoreState.SIMULATING, CoreState.FORECASTING]
        if self.state not in forecast_states:
            return
        if self._scheduler.has_pending_tasks(t_project):
            self._logger.debug('Scheduler has pending tasks. Executing')
            info = TaskRunInfo(t_project=t_project)
            self._logger.debug('Run pending tasks')
            self._scheduler.run_pending_tasks(t_project, info)

    # Scheduled tasks

    def run_forecast(self, task_run_info):
        t_run = task_run_info.t_project
        dt_h = self.settings.value('engine/fc_bin_size', type=float)
        num_bins = self.settings.value('engine/num_fc_bins', type=int)
        # FIXME: do not hardcode  mc, mag_range
        model_input = ModelInput(t_run, self.project, bin_size=dt_h,
                                 mc=0.9, mag_range=(0, 6))
        if self.state == CoreState.SIMULATING:
            model_input.estimate_expected_flow(t_run, self.project,
                                               bin_size=dt_h, num_bins=num_bins)
        else:
            raise NotImplementedError('During "real" forecasting the estimated'
                                      ' flow should be a user input')
        self.forecast_engine.run(model_input)

    def update_rates(self, info):
        t_run = info.t_project
        seismic_events = self.project.seismic_history.events_before(t_run)
        data = [(e.date_time, e.magnitude) for e in seismic_events]
        if len(data) == 0:
            return
        t, m = zip(*data)
        t = list(t)
        m = list(m)
        rates = self.project.rate_history.compute_and_add(m, t, [t_run])
        self._logger.debug('New rate computed: ' + str(rates[0].rate))
