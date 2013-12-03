# -*- encoding: utf-8 -*-
"""
Atlas forecasting engine

See ForecastEngine class documentation for details.
    
"""

from PyQt4 import QtCore
import logging
from datetime import datetime
from isha.common import RunData
from isha.rj import Rj


class ForecastEngineState:
    IDLE = 0
    FORECASTING = 1


class ForecastEngine(QtCore.QObject):
    """
    The forecast engine is responsible for forecast model management.

    The engine manages a collection of forecast models and launches those on
    request. It weights the results and initiates model recalibration when
    necessary.

    .. pyqt4:signal:finished: emitted when all models have finished and results
    are ready to be collected.

    """

    forecast_complete = QtCore.pyqtSignal()

    def __init__(self):
        self.last_forecast_time = None
        self.state = ForecastEngineState.IDLE
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        # initialize models
        rj = Rj(a=-1.6, b=1.0, p=1.2, c=0.05)
        rj.finished.connect(self._on_rj_finished)
        self._models = [rj]
        self._model_states = {rj: ForecastEngineState.IDLE}

    def run(self, h_events, s_events, t):
        """
        Run a new forecast with the events given in the function parameters.

        :param h_events: list of hydraulic events
        :type h_events: list of HydraulicEvent objects
        :param s_events: list of seismic events
        :type s_events: list of SeismicEvent objects
        :param t: forecast time
        :type t: datetime

        """
        # Skip this forecast if the engine is not IDLE
        if self.state != ForecastEngineState.IDLE:
            self.logger.warning('Attempted to initiate forecast while the '
                                'engine is not idle. Skipping forecast at '
                                't=' + str(t))
            return
        self.logger.info('Initiating forecast at t = ' + str(t))
        # Prepare model input
        run_data = RunData()
        run_data.seismic_events = s_events
        run_data.hydraulic_events = h_events
        run_data.forecast_times = [t]
        run_data.forecast_mag_range = (1, 6)
        # Run models
        for model in self._models:
            self._model_states[model] = ForecastEngineState.FORECASTING
            model.prepare_run(run_data)
            model.run()
        self._update_state()

    def get_forecast_results(self):
        pass

    # State handling

    def _update_state(self):
        """ Set the engine state according to the individual model states """
        if ForecastEngineState.FORECASTING in self._model_states.values():
            new_state = ForecastEngineState.FORECASTING
        else:
            new_state = ForecastEngineState.IDLE
        if self.state != new_state:
            self.state = new_state
            if new_state == ForecastEngineState.IDLE:
                self.forecast_complete.emit()

    # Model completion handlers

    def _on_rj_finished(self, model):
        self._model_states[model] = ForecastEngineState.IDLE
        self.logger.debug('RJ run results: ' + str(model.run_results))
        self._update_state()