# -*- encoding: utf-8 -*-
"""
Atlas forecasting engine

Long Description
    
"""

from PyQt4 import QtCore
import logging
from datetime import datetime
from isha.common import RunData


class ForecastEngineState:
    IDLE = 0
    FORECASTING = 1


class ForecastEngine(QtCore.QObject):

    forecast_completed = QtCore.pyqtSignal(datetime)

    def __init__(self):
        self.last_forecast_time = None
        self.state = ForecastEngineState.IDLE
        self.logger = logging.getLogger(__name__)

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
            self.logger.warning('Attempted to initiate forecast while the engine'
                             'is not idle. Skipping forecast at t=' + str(t))
            return

        self.logger.info('Initiating forecast at t=' + str(t))

    def get_forecast_results(self):
        pass