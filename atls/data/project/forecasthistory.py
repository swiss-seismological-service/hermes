# -*- encoding: utf-8 -*-
"""
Manages the history of induced seismicity forecasts

Long Description
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""


from data.project.eventhistory import EventHistory
from data.forecastresult import ForecastResult


class ForecastHistory(EventHistory):
    """
    Provides a history of forecast results and functions to read and write
    them from/to a persistent store. The class uses Qt signals to signal
    changes.

    """

    def __init__(self, store):
        super(ForecastHistory, self).__init__(store, ForecastResult)