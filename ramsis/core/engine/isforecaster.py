# -*- encoding: utf-8 -*-
"""
Ramsis IS forecaster

See `ISForecaster` class documentation for details.

"""

import logging

from PyQt4 import QtCore

import ismodelcontrol as mc
from core.data.isforecastresult import ISForecastResult, ISModelResult


class ISForecastState:
    IDLE = 0  #: Idle state
    FORECASTING = 1  #: Busy state


class ISForecaster(QtCore.QObject):
    """
    The `ISForecaster` runs induced seismicity forecast models.

    The forecaster launches model runs on request. Model run results are of
    type `ISForecastResult` and are returned to the caller by invoking the
    completion handler.

    """

    def __init__(self, completion_handler):
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
        self._running_models = []

        self._run_result = None

    def run(self, model_input):
        """
        Run a new forecast with the events given in the function parameters.

        :param model_input: input for this run
        :type model_input: ModelInput

        """
        t_run = model_input.t_run
        for model in mc.active_models:
            model.finished.connect(self._on_model_run_finished)
        # Skip this forecast if the forecaster is not IDLE
        if self.state != ISForecastState.IDLE:
            self.logger.warning('Attempted to initiate IS forecast while the '
                                'forecaster is not idle. Skipping forecast at '
                                't=' + str(t_run))
            return
        self.state = ISForecastState.FORECASTING
        self.logger.info(6 * '----------')
        self.logger.info('Initiating forecast at t = ' + str(t_run))
        # Perform any pending result validations before we run the next
        # forecast. This will cause model weights to adjust.
        # FIXME: the review process (weighting) will be a separate stage (#17)
        # self.review_results(t_run, model_input.seismic_events)
        self.logger.debug('Expected flow during forecast: {:.1f} l/min.'
                          .format(model_input.expected_flow))
        self.current_run = model_input.t_run
        self._running_models = list(mc.active_models)
        mc.run_active_models(model_input)

    # State handling

    def _update_state(self):
        if not self._running_models:
            t_run = self.current_run
            self.logger.info('Forecast complete for t = ' + str(t_run))
            self.current_run = None
            self.completion_handler(self._run_result)

    # Model completion handlers

    def _on_model_run_finished(self, model):
        """
        Adds the output to the result set for the current run

        :param model: Model that has finished
        :type model_output: Model

        """
        is_model_result = ISModelResult(model.output)
        model_name = model.title
        t_run = is_model_result.t_run
        if self._run_result is None:
            self._run_result = ISForecastResult(t_run)
        self._run_result.model_results[model_name] = is_model_result
        if is_model_result.failed:
            self.logger.warn(model_name + ' did not produce any results for'
                             ' t = ' + str(t_run) + '. Reason: ' +
                             is_model_result.failure_reason)
        else:
            self.logger.debug('Received results for ' + model_name)
        self._running_models.remove(model)
        model.finished.disconnect(self._on_model_run_finished)
        self._update_state()

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
