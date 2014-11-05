# -*- encoding: utf-8 -*-
"""
Atls IS forecaster

See ISForecaster class documentation for details.
    
"""

import logging
from isha.common import ModelInput, ModelState, ModelOutput
from domainmodel.isforecastresult import ISForecastResult, ISModelResult
import ishamodelcontrol as mc
from PyQt4 import QtCore


class ISForecastState:
    IDLE = 0
    FORECASTING = 1


class ISForecaster(QtCore.QObject):
    """
    The IS Forecaster runs induced seismicity forecast models.

    The forecaster launches model runs on request. Model run results are of
    type ISForecastResult and are returned to the caller by invoking the
    completion handler.

    """

    def __init__(self, completion_handler, model_ids=['all']):
        """
        :param completion_handler: callback to invoke on completion of fore-
            cast. Must take exactly one argument which is the forecast result.
        :param model_ids: list of model ids to run (or just 'all')

        """
        super(ISForecaster, self).__init__()
        self.last_forecast_time = None
        self.state = ISForecastState.IDLE
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.current_run = None
        self.completion_handler = completion_handler

        # Load models and prepare runners
        mc.load_models(model_ids)
        self._detached_runners = [mc.DetachedRunner(m)
                                  for m in mc.active_models]

        # Add state information for each model and subscribe to relevant
        # signals
        for model in mc.active_models:
            # The QueuedConnection makes sure the callback runs on our thread
            # and not on the models.
            model.state_changed.connect(self._on_model_state_changed,
                                        type=QtCore.Qt.QueuedConnection)
            model.finished.connect(self._on_model_run_finished,
                                   type=QtCore.Qt.QueuedConnection)

        self.run_result = None

    def run(self, model_input):
        """
        Run a new forecast with the events given in the function parameters.

        :param model_input: input for this run
        :type model_input: ModelInput

        """
        t_run = model_input.t_run
        # Skip this forecast if the forecaster is not IDLE
        if self.state != ISForecastState.IDLE:
            self.logger.warning('Attempted to initiate IS forecast while the '
                                'forecaster is not idle. Skipping forecast at '
                                't=' + str(t_run))
            return
        self.logger.info(6*'----------')
        self.logger.info('Initiating forecast at t = ' + str(t_run))
        # Perform any pending result validations before we run the next
        # forecast. This will cause model weights to adjust.
        # FIXME: the review process (weighting) will be a separate stage (#17)
        # self.review_results(t_run, model_input.seismic_events)
        self.logger.debug('Expected flow during forecast: {:.1f} l/min.'
            .format(model_input.expected_flow))
        self.current_run = model_input.t_run
        for runner in self._detached_runners:
            runner.run_model(model_input)

    # State handling

    def _on_model_state_changed(self):
        if ModelState.RUNNING in [m.state for m in mc.active_models]:
            new_global_state = ISForecastState.FORECASTING
        else:
            new_global_state = ISForecastState.IDLE
        if self.state != new_global_state:
            self.state = new_global_state
            if new_global_state == ISForecastState.IDLE:
                t_run = self.current_run
                self.logger.info('Forecast complete for t = ' + str(t_run))
                self.current_run = None
                self.completion_handler(self.run_result)

    # Model completion handlers

    def _on_model_run_finished(self, model_output):
        """
        Adds the output to the result set for the current run

        :param model_output: Model output for the previous run
        :type model_output: ModelOutput

        """
        is_model_result = ISModelResult(model_output)
        model_name = is_model_result.model_name
        t_run = is_model_result.t_run
        if self.run_result is None:
            self.run_result = ISForecastResult(t_run)
        self.run_result.model_results[model_name] = is_model_result
        if not is_model_result.failed:
            self.logger.warn(model_name + ' did not produce any results for'
                             ' t = ' + str(t_run) + '. Reason: ' +
                             is_model_result.failure_reason)
        else:
            self.logger.debug('Received results for ' + model_name)

    # FIXME: this should go somewhere else (#17)
    # def review_results(self, t, observed_events):
    #     """
    #     Review previous results and assign scores to models
    #
    #     """
    #     # Find results to review
    #     to_review = []
    #     for t_run, output_set in self.output_sets.iteritems():
    #         if t_run < t and not output_set.reviewed:
    #             to_review.append(output_set)
    #
    #     self.logger.info('Computing {} output set score from previous '
    #                      'runs first'.format(len(to_review)))
    #
    #     for output_set in to_review:
    #         output_set.review(observed_events)