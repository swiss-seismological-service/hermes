# -*- encoding: utf-8 -*-
"""
RAMSIS Core Application.

Top level object for the core Ramsis application. Core meaning it is not
aware of any gui components (or other user control facilities). The user
control facilities should be hooked up in the Ramsis class instead.

"""

from collections import namedtuple
import logging
from datetime import timedelta
import os

from PyQt4 import QtCore

from data.project.store import Store
from data.project.ramsisproject import RamsisProject
from data.ormbase import OrmBase
from simulator import Simulator, SimulatorState
from core.engine import Engine, EngineState
import core.ismodelcontrol as mc
from scheduler.taskscheduler import TaskScheduler, ScheduledTask

# from tools import Profiler

# Used internally to pass information to repeating tasks
# t_project is the project time at which the task is launched
TaskRunInfo = namedtuple('TaskRunInfo', 't_project')


class Controller(QtCore.QObject):
    """
    Top level class for RAMSIS i.s.

    Instantiation of this class bootstraps the entire application

    :ivar project: Ramsis Project
    :type project: RamsisProject

    """

    project_loaded = QtCore.pyqtSignal(object)

    def __init__(self, settings):
        """
        Bootstraps the Ramsis core logic

        :param settings: object that holds the app settings
        :type settings: AppSettings

        """
        super(Controller, self).__init__()
        self._settings = settings
        self.project = None
        self.engine = Engine(settings)

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

        :param path: path to the ramsis project file
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
        store = Store(store_path, OrmBase)
        self.project = RamsisProject(store, os.path.basename(path))
        self.project.project_time_changed.connect(self._on_project_time_change)
        self.engine.observe_project(self.project)
        self.project_loaded.emit(self.project)
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
        self.project.close()
        self.project = None
        self.project.project_time_changed.disconnect(
            self._on_project_time_change)

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
        (Re)starts the simulation.

        Replays the events from the seismic history.

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
            task_function=self.engine.update_rates,
            dt=timedelta(minutes=dt),
            name='Rate update')
        scheduler.add_task(rate_update_task)

        return scheduler

    def reset(self, t0):
        """
        Reset core and all schedulers to t0

        """
        self._scheduler.reset_schedule(t0)

    def _on_project_time_change(self, t_project):
        """
        Invoked when the project time changes. Triggers scheduled computations.

        :param t_project: current project time
        :type t_project: datetime

        """
        # Project time changes can also occur on startup or due to manual user
        # interaction. In those cases we don't trigger any computations.
        if self.engine.state == EngineState.INACTIVE:
            return
        if self._scheduler.has_pending_tasks(t_project):
            self._logger.debug('Scheduler has pending tasks. Executing')
            info = TaskRunInfo(t_project=t_project)
            self._logger.debug('Run pending tasks')
            self._scheduler.run_pending_tasks(t_project, info)
