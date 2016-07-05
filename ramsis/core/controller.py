# -*- encoding: utf-8 -*-
"""
RAMSIS Core Controller.

This module defines a single class `Controller` which acts as the
central coordinator for all core components.

"""

from collections import namedtuple
import logging
from datetime import timedelta
import os

from PyQt4 import QtCore

from core.data.store import Store
from core.data.project import Project
from core.data.ormbase import OrmBase
from core.simulator import Simulator, SimulatorState
from core.engine.engine import Engine, EngineState

import core.engine.ismodelcontrol as mc
from core.scheduler import TaskScheduler, ScheduledTask

from web.runners import FDSNWSRunner, HYDWSRunner

# from core.tools import Profiler

TaskRunInfo = namedtuple('TaskRunInfo', 't_project')
"""
Used internally to pass information to repeating tasks
t_project is the project time at which the task is launched

"""


class Controller(QtCore.QObject):
    """
    RT-RAMSIS Core Controller Class

    A singleton instance of `Controller` is created when the program
    launches. The `Controller` is responsible for setting up and connecting
    all other core components, so it effectively bootstraps the application
    logic.

    At run time, the `Controller` acts as the central entry point for
    the user interface.

    :ivar Project project: Currently loaded project
    :param AppSettings settings: reference to the application settings

    """

    project_loaded = QtCore.pyqtSignal(object)

    def __init__(self, settings):
        super(Controller, self).__init__()
        self._settings = settings
        self.project = None
        self.engine = Engine(settings)
        self.fdsnws_previous_end_time = None
        self.hydws_previous_end_time = None
        self.fdsnws_runner = None
        self.hydws_runner = None

        # Load active IS models
        mc.load_models(self._settings.value('ISHA/models'))

        # Initialize simulator
        self.simulator = Simulator(self._simulation_handler)

        # Scheduler
        self._scheduler = self._create_task_scheduler()

        # Time, state and other internals
        self._logger = logging.getLogger(__name__)
        # self._logger.setLevel(logging.DEBUG)

    # Project handling

    def open_project(self, path):
        """
        Open RAMSIS project file located at path

        :param str path: path to the ramsis project file

        """
        if not os.path.exists(path):
            self._logger.error('Could not find project: ' + path)
            return
        # We add an additional / in front of the url. So now we have 3 slashes
        # in total, because host and db-name section are both empty for sqlite
        store_path = 'sqlite:///' + path
        self._logger.info('Loading project at ' + path +
                          ' - This might take a while...')
        store = Store(store_path, OrmBase)
        self.project = Project(store, os.path.basename(path))
        self.project.project_time_changed.connect(self._on_project_time_change)
        self.engine.observe_project(self.project)
        self.project_loaded.emit(self.project)
        self._logger.info('... initializing runners...')
        self.fdsnws_runner = FDSNWSRunner(self._settings)
        self.hydws_runner = HYDWSRunner(self._settings)
        self.fdsnws_runner.finished.connect(self._on_fdsnws_runner_finished)
        self.hydws_runner.finished.connect(self._on_hydws_runner_finished)
        self._logger.info('...done')

    def create_project(self, path):
        """
        Create a new project at path and load it.

        If a project exists at path, it will be replaced.

        """
        if self.project:
            self.close_project()
        if os.path.exists(path):
            os.remove(path)
        store_path = 'sqlite:///' + path
        self._logger.info('Creating project at ' + path)
        store = Store(store_path, OrmBase)
        store.commit()
        store.close()
        self.open_project(path)

    def close_project(self):
        """
        Close the current project.

        """
        self.project.close()
        self.project.project_time_changed.disconnect(
            self._on_project_time_change)
        self.project = None

    # Running

    def start(self):
        if self._settings.value('enable_lab_mode'):
            self.start_simulation()
        else:
            self._logger.notice('RAMSIS only works in lab mode at the moment')

    def pause(self):
        if self._settings.value('enable_lab_mode'):
            self.pause_simulation()

    def stop(self):
        if self._settings.value('enable_lab_mode'):
            self.stop_simulation()

    # Simulation

    def start_simulation(self):
        """
        Starts the simulation.

        The simulation replays the events from the seismic and hydraulic
        histories at the simulation speed that is currently configured and
        triggers forecasts and other computations at the appropriate times.
        See :doc:`core` documentation for further information on how simulation
        works.

        If the simulation was previously paused by `pause_simulation` the
        simulation will simply continue. Otherwise, the simulator will be
        reset to the start of its :meth:`configured
        <core.simulator.Simulator.configure>` time range and begin from there.

        """
        # self._profiler = Profiler()
        # self._profiler.start()
        if self.project is None:
            return
        self._logger.info('Starting simulation')
        if self.simulator.state == SimulatorState.STOPPED:
            self._init_simulation()
        # Start simulator
        self.simulator.start()

    def _init_simulation(self):
        """
        (Re)initialize simulator and scheduler for a new simulation

        """
        self._logger.info(
            'Deleting any forecasting results from previous runs')
        self.project.forecast_history.clear()
        # Reset task scheduler based on the first simulation step time
        time_range = self._simulation_time_range()
        inf_speed = self._settings.value('lab_mode/infinite_speed')
        if inf_speed:
            self._logger.info('Simulating at maximum speed')
            dt_h = self._settings.value('engine/fc_interval')
            dt = timedelta(hours=dt_h)
            step_signal = self.engine.forecast_complete
            self.simulator.configure(time_range, step_on=step_signal, dt=dt)
        else:
            speed = self._settings.value('lab_mode/speed')
            self._logger.info('Simulating at {:.0f}x'.format(speed))
            self.simulator.configure(time_range, speed=speed)
        self.reset(time_range[0])

    def pause_simulation(self):
        """ Pauses the simulation. """
        self._logger.info('Pausing simulation')
        self.simulator.pause()

    def stop_simulation(self):
        """ Stops the simulation """
        self.simulator.stop()
        self._logger.info('Stopping simulation')

    def _simulation_time_range(self):
        event_time_range = self.project.event_time_range()
        start_date = self._settings.date_value('lab_mode/forecast_start')
        start_date = start_date if start_date else event_time_range[0]
        end_date = event_time_range[1]
        return start_date, end_date

    # Simulation handling

    def _simulation_handler(self, simulation_time):
        """ Invoked by the simulation whenever the project time changes """
        self.project.update_project_time(simulation_time)

    # Scheduler management

    def _create_task_scheduler(self):
        """
        Creates the task scheduler and schedules recurring tasks

        """
        scheduler = TaskScheduler()

        # Forecasting Task
        dt = self._settings.value('engine/fc_interval')
        forecast_task = ScheduledTask(
            task_function=self.engine.run_forecast,
            dt=timedelta(hours=dt),
            name='Forecast')
        scheduler.add_task(forecast_task)
        self.engine._forecast_task = forecast_task  # keep reference for later

        # Rate computations
        dt = self._settings.value('engine/rt_interval')
        rate_update_task = ScheduledTask(
            task_function=self._update_rates,
            dt=timedelta(minutes=dt),
            name='Rate update')
        scheduler.add_task(rate_update_task)

        # Fetching seismic data over fdsnws
        minutes = self._settings.value('data_acquisition/fdsnws_interval')
        task = ScheduledTask(task_function=self._import_fdsnws_data,
                             dt=timedelta(minutes=minutes),
                             name='FDSNWS')
        scheduler.add_task(task)

        # Fetching hydraulic data
        minutes = self._settings.value('data_acquisition/hydws_interval')
        task = ScheduledTask(task_function=self._import_hydws_data,
                             dt=timedelta(minutes=minutes),
                             name='HYDWS')
        scheduler.add_task(task)

        return scheduler

    def reset(self, t0):
        """
        Reset core and all schedulers to t0

        """
        self._scheduler.reset_schedule(t0)

    def _on_project_time_change(self, t_project):
        """
        Invoked when the project time changes.

        Checks if the `TaskScheduler` has pending tasks at the new project
        time and, if yes, executes them.

        :param t_project: current project time
        :type t_project: datetime

        """
        # Project time changes can also occur on startup or due to manual user
        # interaction. In those cases we don't trigger any computations.
        # FIXME: Don't make this dependent on the eng. state (see issue #11)
        if self.engine.state == EngineState.INACTIVE:
            return
        if self._scheduler.has_pending_tasks(t_project):
            self._logger.debug('Scheduler has pending tasks. Executing')
            info = TaskRunInfo(t_project=t_project)
            self._logger.debug('Run pending tasks')
            self._scheduler.run_pending_tasks(t_project, info)

    # FDSNWS task function

    def _import_fdsnws_data(self, run_info):
        self.fdsnws_runner.start()

    def _on_fdsnws_runner_finished(self, results):
        if results is not None:
            self.project.seismic_history.import_events(**results)

    # HYDWS task function

    def _import_hydws_data(self, run_info):
        self.hydws_runner.start()

    def _on_hydws_runner_finished(self, results):
        if results is not None:
            self.project.hydraulic_history.import_events(**results)

    # Rate computation task function

    def _update_rates(self, info):
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
