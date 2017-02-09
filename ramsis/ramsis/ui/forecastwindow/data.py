# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2015, SED (ETH Zurich)

"""

from PyQt4.QtCore import pyqtSignal, QObject
from datetime import datetime
from ramsisdata.forecast import ForecastSet, Forecast, ForecastInput,\
    ForecastResult, Scenario, SkillTest, ModelResult, RatePrediction


class DummyProject(QObject):
    will_close = pyqtSignal()
    project_time_changed = pyqtSignal()

    def __init__(self, fc_set):
        super(DummyProject, self).__init__()
        self.forecast_set = fc_set

def dummy_data():
    fc_set = ForecastSet()

    forecast = Forecast()
    forecast.forecast_time = datetime(2016, 11, 11, 12, 00, 00)
    forecast_result = ForecastResult()
    forecast.result.append(forecast_result)
    model_result = ModelResult()
    model_result.model_name = 'rj'
    forecast.result[0].model_results[model_result.model_name] = model_result
    model_result = ModelResult()
    model_result.model_name = 'etas'
    forecast.result[0].model_results[model_result.model_name] = model_result
    forecast.input = ForecastInput()
    scenario = Scenario()
    scenario.name = 'Scenario 1'
    forecast.input.scenarios.append(scenario)
    scenario = Scenario()
    scenario.name = 'Scenario 2'
    forecast.input.scenarios.append(scenario)
    fc_set.forecasts.append(forecast)

    return DummyProject(fc_set)

