# -*- encoding: utf-8 -*-
"""
Manages the history of induced seismicity forecasts

Long Description
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""


from eventhistory import EventHistory
from domainmodel.isforecastresult import ISForecastResult


class ISForecastHistory(EventHistory):
    """
    Provides a history of IS forecast results and functions to read and write
    them from/to a persistent store. The class uses Qt signals to signal
    changes.

    """

    def __init__(self, store):
        super(ISForecastHistory, self).__init__(store, ISForecastResult)