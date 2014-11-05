# -*- encoding: utf-8 -*-
"""
The engine handles time dependent tasks on the project.

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""


from project.atlsproject import AtlsProject
from taskscheduler import TaskScheduler, ScheduledTask
from isha.common import ModelInput
from isforecaster import ISForecaster
from PyQt4 import QtCore
from datetime import timedelta
from collections import namedtuple


# Used internally to pass information to repeating tasks
# t_project is the project time at which the task is launched
TaskRunInfo = namedtuple('TaskRunInfo', 't_project')


class EngineState:
    """
    The engine state switches from inactive to ready as soon as project is
    associated with the engine.
    The busy states indicates that the engine is currently running a forecast
    and is thus not ready for another one.

    """
    INACTIVE = 0
    READY = 1
    BUSY = 2


class Engine(QtCore.QObject):
    """
    An engine is closely linked to the project and handles all time dependent
    tasks on the project such as forecast scheduling, regular rate computations
    etc. It owns a scheduler where it queues tasks and it reacts to the
    project_time_change signal from its associated project.

    """

    # Signals
    state_changed = QtCore.pyqtSignal(int)
    # FIXME: this is currently only consumed by the simulator to step in inf
    # speed mode. We could probably use a simple function call for that (though
    # we need to be careful not to starve the run loop). The Ui updates from
    # project emitted change signals.
    forecast_complete = QtCore.pyqtSignal()

    def __init__(self):
        """
        :param project: Project to observe on time changes
        :type project: AtlsProject

        """
        super(Engine, self).__init__()
        self._project = None
        self._forecast_task = None
        self._state = EngineState.INACTIVE
        self._is_forecaster = None  # Currently active forecaster -> job

    @property
    def t_next_forecast(self):
        return self._forecast_task.run_time

    @property
    def state(self):
        return self._state

    def observe_project(self, project):
        project.project_time_changed.connect(self._on_project_time_change)
        project.will_close.connect(self._on_project_close)
        self._project = project

    def _on_project_close(self, project):
        project.project_time_changed.disconnect(self._on_project_time_change)
        project.will_close.disconnect(self._on_project_close)
        self._project = None
        self._transition_to_state(EngineState.INACTIVE)

    def _on_project_time_change(self, t_project):
        """
        Invoked when the project time changes. Triggers scheduled computations.

        :param t_project: current project time
        :type t_project: datetime

        """
        # Project time changes can also occur on startup or due to manual user
        # interaction. In those cases we don't trigger any computations.
        if self.state == EngineState.INACTIVE:
            return
        if self._scheduler.has_pending_tasks(t_project):
            self._logger.debug('Scheduler has pending tasks. Executing')
            info = TaskRunInfo(t_project=t_project)
            self._logger.debug('Run pending tasks')
            self._scheduler.run_pending_tasks(t_project, info)

    # State transitions

    def _transition_to_state(self, state):
        self._state = state
        self.state_changed.emit(state)

    # Scheduler management

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

    # Scheduled task functions

    def run_forecast(self, task_run_info):
        t_run = task_run_info.t_project
        mode = task_run_info.mode
        dt_h = self.settings.value('engine/fc_bin_size', type=float)
        self._create_and_run_fc_job(t_run, mode, dt_h)

    def update_rates(self, info):
        t_run = info.t_project
        # FIXME: do not hardcode  mc
        seismic_events = self.project.seismic_history.events_before(t_run)
        data = [(e.date_time, e.magnitude) for e in seismic_events]
        if len(data) == 0:
            return
        t, m = zip(*data)
        t = list(t)
        m = list(m)
        rates = self.project.rate_history.compute_and_add(m, t, [t_run])
        self._logger.debug('New rate computed: ' + str(rates[0].rate))

    # Temporary methods (to be factored out)

    # TODO: job will be its own class soon (#17)
    def _create_and_run_fc_job(self, t_run, mode, dt_h):
        """
        Run a new forecast job

        """
        assert(self.state != EngineState.INACTIVE)

        # Skip this forecast if the engine is busy
        if self.state == EngineState.BUSY:
            self.logger.warning('Attempted to initiate forecast while the '
                                'engine is still busy with a previously'
                                'started forecast. Skipping at '
                                't=' + str(t_run))
            return

        self.logger.info(6*'----------')
        self.logger.info('Initiating forecast at t = ' + str(t_run))

        # FIXME: do not hard code mc, mag_range
        model_input = ModelInput(t_run, self.project, bin_size=dt_h,
                                 mc=0.9, mag_range=(0, 6))
        model_input.estimate_expected_flow(t_run, self.project, dt_h)
        # TODO: Allow estimated flow to be user defined (#18)
        self.is_forecaster = ISForecaster(self.fc_complete,
                                          self.settings.value('ISHA/models'))
        self.is_forecaster.run(model_input)
        self._transition_to_state(EngineState.BUSY)

    # Task completion handlers

    def fc_complete(self, result):
        self.project.is_forecast_history.add(result)
        self.forecast_complete.emit()
        self._transition_to_state(EngineState.READY)
