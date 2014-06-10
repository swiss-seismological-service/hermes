# -*- encoding: utf-8 -*-
"""
Atls forecasting engine

See ForecastEngine class documentation for details.
    
"""

from PyQt4 import QtCore
import logging
from isha.common import ModelInput, ModelState, ModelOutput
import ishamodelcontrol as mc


class ForecastEngineState:
    IDLE = 0
    FORECASTING = 1

class OutputSet:
    """
    A OutputSet holds the outputs from all models for the forecast at t_run

    """
    def __init__(self, t_run):
        """
        :param t_run: time of the model run
        :type t_run: datetime

        """
        self.t_run = t_run
        self._reviewed = False
        self.model_outputs = {}

    @property
    def reviewed(self):
        return self._reviewed

    def review(self, observed_events):
        for result in self.model_outputs.itervalues():
            result.review(observed_events)
        self._reviewed = True


class ForecastEngine(QtCore.QObject):
    """
    The forecast engine runs ISHA models.

    The engine launches model runs on request. Model run results are archived
    in the result_sets dictionary which is structured as followed:

    result_sets: { t_run : { model: output }
                   t_run : { model: output }
                   ...
                 }

    where *t_run* is the run identifier that was given in run_input, *model*
    is the model object and output is the ModelOutput object that resulted
    from the model run.

    .. pyqt4:signal:forecast_complete: emitted when all models have finished
    and results are ready to be collected. The payload contains the specific
    output set for the run.

    """

    forecast_complete = QtCore.pyqtSignal(object)

    def __init__(self, model_ids=['all']):
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

        # Initialize output sets
        self.output_sets = {}

    def run(self, model_input):
        """
        Run a new forecast with the events given in the function parameters.

        :param model_input: input for this run
        :type model_input: ModelInput

        """
        t_run = model_input.t_run
        # Skip this forecast if the engine is not IDLE
        if self.state != ForecastEngineState.IDLE:
            self.logger.warning('Attempted to initiate forecast while the '
                                'engine is not idle. Skipping forecast at '
                                't=' + str(t_run))
            return
        self.logger.info(6*'----------')
        self.logger.info('Initiating forecast at t = ' + str(t_run))
        # Perform any pending result validations before we run the next
        # forecast. This will cause model weights to adjust.
        self.review_results(t_run, model_input.seismic_events)
        self.logger.debug('Expected flow during forecast: {:.1f} l/min.' \
            .format(model_input.expected_flow))
        self.current_run = model_input.t_run
        for runner in self._detached_runners:
            runner.run_model(model_input)

    # State handling

    def _on_model_state_changed(self):
        if ModelState.RUNNING in [m.state for m in mc.active_models]:
            new_global_state = ForecastEngineState.FORECASTING
        else:
            new_global_state = ForecastEngineState.IDLE
        if self.state != new_global_state:
            self.state = new_global_state
            if new_global_state == ForecastEngineState.IDLE:
                t_run = self.current_run
                self.logger.info('Forecast complete for t = ' + str(t_run))
                self.current_run = None
                self.forecast_complete.emit(self.output_sets.get(t_run))


    # Model completion handlers

    def _on_model_run_finished(self, model_output):
        """
        Adds the output to the result set for the current run

        :param model_output: Run results for the previous run
        :type model_output: ModelOutput

        """
        model = model_output.model
        t_run = model_output.t_run
        output_set = self.output_sets.get(t_run)
        if output_set is None:
            output_set = OutputSet(t_run)
            self.output_sets[t_run] = output_set
        output_set.model_outputs[model] = model_output
        if not model_output.has_results:
            self.logger.warn(model.title + ' did not produce any results for'
                             ' t = ' + str(t_run) + '. Reason: ' +
                             model_output.no_result_reason)
        else:
            self.logger.debug('Stored results for ' + model.title)


    def review_results(self, t, observed_events):
        """
        Review previous results and assign scores to models

        """
        # Find results to review
        to_review = []
        for t_run, output_set in self.output_sets.iteritems():
            if t_run < t and not output_set.reviewed:
                to_review.append(output_set)

        self.logger.info('Computing {} output set score from previous '
                         'runs first'.format(len(to_review)))

        for output_set in to_review:
            output_set.review(observed_events)