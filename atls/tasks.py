# -*- encoding: utf-8 -*-
"""
Celery Tasks

Long Description
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from celery import Celery
from celery.utils.log import get_task_logger

from isha.common import ModelInput
from isforecaster import ISForecaster

celery = Celery('tasks')
logger = get_task_logger(__name__)


@celery.task
def is_forecast(inputs):
    t_run = inputs['t_run']
    dt_h = inputs['dt_h']
    project = inputs['project']

    logger.info(6*'----------')
    logger.info('Initiating forecast at t = ' + str(t_run))

    # FIXME: do not hard code mc, mag_range
    model_input = ModelInput(t_run, project, bin_size=dt_h, mc=0.9,
                             mag_range=(0, 6))
    model_input.estimate_expected_flow(t_run, self._project, dt_h)
    # TODO: Allow estimated flow to be user defined (#18)
    self.is_forecaster = ISForecaster(self.fc_complete)
    self._transition_to_state(EngineState.BUSY)
    self.is_forecaster.run(model_input)