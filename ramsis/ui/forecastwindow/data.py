# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2015, SED (ETH Zurich)

"""

from PyQt4.QtCore import pyqtSignal, QObject
from datetime import datetime
from core.data.forecast import ForecastSet, Forecast, ForecastInput,\
    ForecastResult, Scenario, SkillTest, ModelResult, RatePrediction


class DummyProject(QObject):
    will_close = pyqtSignal()
    project_time_changed = pyqtSignal()

    def __init__(self, fc_set):
        super(DummyProject, self).__init__()
        self.forecast_set = fc_set

def dummy_data():
    fc_set = ForecastSet(store=None)

    forecast = Forecast()
    forecast.forecast_time = datetime(2016, 11, 11, 12, 00, 00)
    forecast.input = ForecastInput()
    scenario = Scenario()
    scenario.name = 'Scenario 1'
    forecast.input.scenarios.append(scenario)
    scenario = Scenario()
    scenario.name = 'Scenario 2'
    forecast.input.scenarios.append(scenario)
    fc_set.forecasts.append(forecast)

    return DummyProject(fc_set)

