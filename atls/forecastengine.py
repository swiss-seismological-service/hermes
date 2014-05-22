# -*- encoding: utf-8 -*-
"""
Atls forecasting engine

See ForecastEngine class documentation for details.
    
"""

from PyQt4 import QtCore
import logging
from isha.common import ModelInput
import ishamodelcontrol as mc


class ForecastEngineState:
    IDLE = 0
    FORECASTING = 1


class ForecastEngine(QtCore.QObject):
    """
    The forecast engine runs ISHA models.

    The engine manages a collection of forecast models and launches model runs
    on request. Model run results are archived in the result_sets dictionary
    which is structured as followed:

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

    """

    forecast_complete = QtCore.pyqtSignal(dict)

    def __init__(self):
        super(ForecastEngine, self).__init__()
        self.last_forecast_time = None
        self.state = ForecastEngineState.IDLE
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        # Load models and prepare runners
        self._models = mc.load_models()
        self._detached_runners = [mc.DetachedRunner(m) for m in self._models]

        # Add state information for each model and subscribe to relevant signals
        self._model_states = {}
        for model in self._models:
            self._model_states[model] = ForecastEngineState.IDLE
            # The QueuedConnection makes sure the callback runs on our thread
            # and not on the models.
            model.finished.connect(self._on_model_run_finished,
                                   type=QtCore.Qt.QueuedConnection)

        # Initialize result sets
        self.result_sets = {}

    @property
    def models(self):
        return self._models

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

        # TODO: look at this again
        # The following cannot be accomplished in one step, since some models
        # run asynchronously and might finish before _update_state gets called

        # Prepare models
        for model in self._models:
            self._model_states[model] = ForecastEngineState.FORECASTING
        self._update_global_state()
        # Run models in detached threads
        for runner in self._detached_runners:
            runner.run_model(run_input)

    # State handling

    def _update_global_state(self, t_run=None):
        """ Set the engine state according to the individual model states """
        if ForecastEngineState.FORECASTING in self._model_states.values():
            new_state = ForecastEngineState.FORECASTING
        else:
            new_state = ForecastEngineState.IDLE
        if self.state != new_state:
            self.state = new_state
            if new_state == ForecastEngineState.IDLE:
                self.logger.info('Forecast complete')
                self.forecast_complete.emit(self.result_sets.get(t_run))

    # Model completion handlers

    def _register_run_results(self, results):
        run_id = results.t_run
        result_set = self.result_sets.get(run_id)
        if result_set is None:
            result_set = {}
            self.result_sets[run_id] = result_set
        result_set[results.model] = results

    def _on_model_run_finished(self, run_results):
        model = run_results.model
        self._model_states[model] = ForecastEngineState.IDLE
        self._register_run_results(run_results)
        self.logger.debug('Model run complete: ' + model.title)
        self._update_global_state(run_results.t_run)