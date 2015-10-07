# -*- encoding: utf-8 -*-
"""
The `engine` module handles everything that is related to computing
forecasts (see also :doc:`engine`). The central class is `Engine` which is
responsible for setting up `ForecastJob`\s and coordinating between the
different stages of a forecast.

The `Engine` maintains an internal state machine with three possible `states
<EngineState>`.


Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from datetime import timedelta
from collections import namedtuple
import logging

from PyQt4 import QtCore

from data.forecastresult import ForecastResult
from scheduler.taskscheduler import TaskScheduler, ScheduledTask
from ramsisjob import ForecastJob


TaskRunInfo = namedtuple('TaskRunInfo', 't_project')
"""
Used internally to pass information to repeating tasks
t_project is the project time at which the task is launched
"""


class EngineState:
    """
    Defines the possible states of `Engine`.

    The `EngineState` goes from `INACTIVE` to `READY` as soon as a project is
    set through `observe_project`.

    """
    INACTIVE = 0  #: No project is loaded, the `Engine` won't do anything
    READY = 1  #: The `Engine` is ready to start a new forecast
    BUSY = 2  #: The `Engine` is busy computing a forecast

    @classmethod
    def text(cls, state):
        """
        Returns a text representation of `state`

        :param EngineState state: State for which a text representation should
            be returned.

        """
        if state == cls.INACTIVE:
            return 'inactive'
        elif state == cls.READY:
            return 'ready'
        else:
            return 'busy'


class Engine(QtCore.QObject):
    """
    The `Engine` handles forecasting.

    When no project is set, the `Engine` is in the `INACTIVE` state. Once a
    project is loaded, the `Controller` invokes `observe_project` and the
    engine transitions to `READY`.

    In `READY` state, a new forecast can be initiated by calling
    `run_forecast`. The `Engine` will then assemble the input for the
    forecast, transition to the `BUSY` state and initiate the first forecast
    stage. After all stages have completed, the `Engine` emits the
    `forecast_complete` signal and transitions back to the `READY` state.

    :param AppSettings settings: Application settings

    """

    # Signals
    state_changed = QtCore.pyqtSignal(int)
    # FIXME: this is currently only consumed by the simulator to step in inf
    # speed mode. We could probably use a simple function call for that (though
    # we need to be careful not to starve the run loop). The Ui updates from
    # project emitted change signals.
    forecast_complete = QtCore.pyqtSignal()
    """
    Signal emitted by the `Engine` when the current forecast has completed.

    """

    def __init__(self, settings):

        super(Engine, self).__init__()
        self._settings = settings
        self._project = None
        self._forecast_task = None
        self._state = EngineState.INACTIVE
        self._current_fc_job = None  # Currently active forecast job
        self._current_fc_result = None
        self._scheduler = self._create_task_scheduler()
        self._logger = logging.getLogger(__name__)

    @property
    def t_next_forecast(self):
        return self._forecast_task.run_time

    @property
    def state(self):
        """
        :return EngineState: The current state of the `Engine`

        """
        return self._state

    def observe_project(self, project):
        """
        Start observing a new project and set the engine to `READY`

        :param RamsisProject project: Project to observe

        """
        project.project_time_changed.connect(self._on_project_time_change)
        project.will_close.connect(self._on_project_close)
        self._project = project
        self._transition_to_state(EngineState.READY)

    def reset(self, t0):
        """
        Reset core and all schedulers to t0

        """
        self._scheduler.reset_schedule(t0)

    def _on_project_close(self, project):
        project.project_time_changed.disconnect(self._on_project_time_change)
        project.will_close.disconnect(self._on_project_close)
        self._project = None
        self._transition_to_state(EngineState.INACTIVE)

    def _on_project_time_change(self, t_project):
        """
        Invoked when the project time changes. Triggers scheduled computations.

        :param datetime t_project: current project time

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
        self._logger.info(EngineState.text(state))
        self._state = state
        self.state_changed.emit(state)

    # Scheduler management

    def _create_task_scheduler(self):
        """
        Creates the task scheduler and schedules recurring tasks

        """
        scheduler = TaskScheduler()

        # Forecasting Task
        dt = self._settings.value('engine/fc_interval')
        forecast_task = ScheduledTask(task_function=self.run_forecast,
                                      dt=timedelta(hours=dt),
                                      name='Forecast')
        scheduler.add_task(forecast_task)
        self._forecast_task = forecast_task  # keep a reference for later

        # Rate computations
        dt = self._settings.value('engine/rt_interval')
        rate_update_task = ScheduledTask(task_function=self.update_rates,
                                         dt=timedelta(minutes=dt),
                                         name='Rate update')
        scheduler.add_task(rate_update_task)

        return scheduler

    # Scheduled task functions

    def run_forecast(self, task_run_info):
        """
        Run a new forecast.

        If the `Engine` is in `READY` state this will initiate a new forecast.
        Otherwise the method does nothing.

        The parameter `task_run_info` contains all the information the engine
        needs to start a forecast, particularly the forecast time. Upon
        invocation `run_forecast` creates a new `ForecastJob` and assembles
        the input data for the job. It then transitions to the `BUSY` state
        and calls :meth:`core.ramsisjob.ForecastJob.run` to set the job in
        motion.

        :param TaskRunInfo task_run_info: Forecast info such as the forecast
           time.

        """
        assert self.state != EngineState.INACTIVE
        t_run = task_run_info.t_project

        # Skip this forecast if the core is busy
        if self.state == EngineState.BUSY:
            self._logger.warning('Attempted to initiate forecast while the '
                                 'core is still busy with a previously'
                                 'started forecast. Skipping at '
                                 't=' + str(t_run))
            return

        self._logger.info(6 * '----------')
        self._logger.info('Initiating forecast')

        job_input = {
            't_run': t_run,
            'dt_h': self._settings.value('engine/fc_bin_size'),
            'project': self._project
        }
        job = ForecastJob()
        job.stage_completed.connect(self.fc_stage_complete)
        self._current_fc_job = job
        self._current_fc_result = ForecastResult(t_run)
        persist = self._settings.value('engine/persist_results')
        self._project.forecast_history.add(self._current_fc_result, persist)
        self._transition_to_state(EngineState.BUSY)
        self._current_fc_job.run(job_input)

    def update_rates(self, info):
        t_run = info.t_project
        # FIXME: do not hardcode  mc
        seismic_events = self._project.seismic_history.events_before(t_run)
        data = [(e.date_time, e.magnitude) for e in seismic_events]
        if len(data) == 0:
            return
        t, m = zip(*data)
        t = list(t)
        m = list(m)
        rates = self._project.rate_history.compute_and_add(m, t, [t_run])
        self._logger.debug('New rate computed: ' + str(rates[0].rate))

    # Task completion handlers

    def fc_stage_complete(self, stage):
        if stage.stage_id == 'is_forecast_stage':
            self._logger.info('IS forecast stage completed')
            self._current_fc_result.is_forecast_result = stage.results
        elif stage.stage_id == 'psha_stage':
            self._logger.info('PSHA stage completed')
            self._current_fc_result.hazard_oq_calc_id = stage.results['job_id']
        elif stage.stage_id == 'risk_poe_stage':
            self._logger.info('Risk PoE stage completed')
            self._current_fc_result.risk_oq_calc_id = stage.results['job_id']
        else:
            raise ValueError('Unexpected stage id: {}'.format(stage.stage_id))

        if stage == self._current_fc_job.stage_objects[-1]:
            self._transition_to_state(EngineState.READY)
            self.forecast_complete.emit()

        self._current_fc_result.commit_changes()
