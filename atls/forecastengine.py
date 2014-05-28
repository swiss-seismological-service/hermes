# -*- encoding: utf-8 -*-
"""
Atls forecasting engine

See ForecastEngine class documentation for details.
    
"""

from PyQt4 import QtCore
import logging
from isha.common import ModelInput, ModelState, RunResults
import ishamodelcontrol as mc


class ForecastEngineState:
    IDLE = 0
    FORECASTING = 1


class ForecastEngine(QtCore.QObject):
    """
    The forecast engine runs ISHA models.

    The engine launches model runs on request. Model run results are archived
    in the result_sets dictionary which is structured as followed:

    result_sets: { t_run : { model: run_results }
                   t_run : { model: run_results }
                   ...
                 }

    where *t_run* is the run identifier that was given in run_input, *model*
    is the model object and run_results is the RunResults object that resulted
    from the model run.

    .. pyqt4:signal:finished: emitted when all models have finished and results
    are ready to be collected. The payload contains the specific result set for
    the run.

    :param model_ids: model_ids of models to load
    :type model_ids: str

    """

    forecast_complete = QtCore.pyqtSignal(dict)

    def __init__(self, model_ids='all'):
        super(ForecastEngine, self).__init__()
        self.last_forecast_time = None
        self.state = ForecastEngineState.IDLE
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.current_run = None

        # Load models and prepare runners
        mc.load_models(model_ids)
        self._detached_runners = [mc.DetachedRunner(m)
                                  for m in mc.active_models]

        # Add state information for each model and subscribe to relevant signals
        for model in mc.active_models:
            # The QueuedConnection makes sure the callback runs on our thread
            # and not on the models.
            model.state_changed.connect(self._on_model_state_changed,
                                        type=QtCore.Qt.QueuedConnection)
            model.finished.connect(self._on_model_run_finished,
                                   type=QtCore.Qt.QueuedConnection)

        # Initialize result sets
        self.result_sets = {}

    def run(self, run_input):
        """
        Run a new forecast with the events given in the function parameters.

        :param run_input: input for this run
        :type run_input: ModelInput

        """
        # Skip this forecast if the engine is not IDLE
        if self.state != ForecastEngineState.IDLE:
            self.logger.warning('Attempted to initiate forecast while the '
                                'engine is not idle. Skipping forecast at '
                                't=' + str(run_input.t_run))
            return
        self.logger.info('Initiating forecast at t = ' +
                         str(run_input.t_run))
        self.current_run = run_input.t_run
        for runner in self._detached_runners:
            runner.run_model(run_input)

    # State handling

    def _on_model_state_changed(self):
        if ModelState.RUNNING in [m.state for m in mc.active_models]:
            new_global_state = ForecastEngineState.FORECASTING
        else:
            new_global_state = ForecastEngineState.IDLE
        if self.state != new_global_state:
            self.state = new_global_state
            if new_global_state == ForecastEngineState.IDLE:
                t_run = self.current_run;
                self.logger.info('Forecast complete for t = ' + str(t_run))
                self.current_run = None;
                self.forecast_complete.emit(self.result_sets.get(t_run))


    # Model completion handlers

    def _on_model_run_finished(self, run_results):
        """
        Adds the run_results to the result set for the current run

        :param run_results: Run results for the previous run
        :type run_results: RunResults

        """
        model = run_results.model
        run_id = run_results.t_run
        result_set = self.result_sets.get(run_id)
        if result_set is None:
            result_set = {}
            self.result_sets[run_id] = result_set
        result_set[run_results.model] = run_results
        if not run_results.has_results:
            self.logger.warn(model.title + ' did not produce any results for'
                             ' t = ' + str(run_id) + '. Reason: ' +
                             run_results.no_result_reason)

        else:
            self.logger.debug('Stored results for ' + model.title)

