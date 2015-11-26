# -*- encoding: utf-8 -*-
# Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED
"""
Provides Ramsis specific control functions for ISHA models. The `load_models()`
function is the central place where models are loaded to be used in RAMSIS.
I.e. this is also the place where you add new models to the system.

"""

import logging

from detachedrunners import ModelRunner
from ismodels.rj import Rj
from ismodels.etas import Etas

active_models = []
_detached_runners = []


def load_models(model_ids):
    """
    Load ISHA models. Register new models here.

    To add a new model, simply instantiate it, give it a display title
    and add it to the list of models.

    """
    global _detached_runners
    load_all = True if 'all' in model_ids else False

    # Reasenberg Jones
    if load_all or 'rj' in model_ids:
        rj_model = Rj(a=-1.6, b=1.58, p=1.2, c=0.05)
        rj_model.title = 'Reasenberg-Jones'
        active_models.append(rj_model)

    # ETAS
    if load_all or 'etas' in model_ids:
        etas_model = Etas(alpha=0.8, k=8.66, p=1.2, c=0.01, mu=12.7, cf=1.98)
        etas_model.title = 'ETAS'
        active_models.append(etas_model)

    # Shapiro
    # TODO: Re-enable. Temp. disabled bc matlab is not installed on vagrant
    # if load_all or 'shapiro' in model_ids:
    #     shapiro_model = Shapiro()
    #     shapiro_model.title = 'Shapiro (Spatial)'
    #     active_models.append(shapiro_model)

    # This moves the models to their own thread. Do not access model
    # members directly after this line
    _detached_runners = [ModelRunner(m) for m in active_models]

    titles = [m.title for m in active_models]
    logging.getLogger(__name__).info('Loaded models: ' + ', '.join(titles))


def run_active_models(model_input):
    for runner in _detached_runners:
        runner.run_model(model_input)
