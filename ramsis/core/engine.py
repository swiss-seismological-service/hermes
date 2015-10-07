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

import logging

from PyQt4 import QtCore

from data.forecastresult import ForecastResult
from ramsisjob import ForecastJob


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
        project.will_close.connect(self._on_project_close)
        self._project = project
        self._transition_to_state(EngineState.READY)

    def _on_project_close(self, project):
        project.will_close.disconnect(self._on_project_close)
        self._project = None
        self._transition_to_state(EngineState.INACTIVE)

    # State transitions

    def _transition_to_state(self, state):
        self._logger.info(EngineState.text(state))
        self._state = state
        self.state_changed.emit(state)

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
