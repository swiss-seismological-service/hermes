# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2015, SED (ETH Zurich)

"""

from PyQt4.QtCore import pyqtSignal, QObject
from datetime import datetime, timedelta
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

    start = datetime(2016, 1, 1, 06, 00, 00)
    for i in range(5):
        forecast = Forecast()
        forecast.forecast_time = start + timedelta(hours=i*6)
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

