# -*- encoding: utf-8 -*-
# Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED
"""
Provides Ramsis specific control functions for ISHA models. The `load_models()`
function is the central place where models are loaded to be used in RAMSIS.
I.e. this is also the place where you add new models to the system.

"""

import logging

from modelclient import ModelClient

active_models = []
clients = []


def load_models(model_ids, settings):
    """
    Load ISHA models. Register new models here.

    To add a new model, simply instantiate it, give it a display title
    and add it to the list of models.

    """
    global clients
    load_all = True if 'all' in model_ids else False

    # Reasenberg Jones
    if load_all or 'rj' in model_ids:
        model = {
            'model': 'rj',
            'title': 'Reasenberg-Jones',
            'parameters': {'a': -1.6, 'b': 1.58, 'p': 1.2, 'c': 0.05}
        }
        active_models.append(model)

    # ETAS
    if load_all or 'etas' in model_ids:
        model = {
            'model': 'etas',
            'title': 'ETAS',
            'parameters': {'alpha': 0.8, 'k': 8.66, 'p': 1.2, 'c': 0.01,
                           'mu': 12.7, 'cf': 1.98}
        }
        active_models.append(model)

    # Shapiro
    # TODO: Re-enable. Temp. disabled bc matlab is not installed on vagrant
    # if load_all or 'shapiro' in model_ids:
    #     model = {
    #         'model': 'shapiro',
    #         'title': 'Shapiro (spatial)',
    #         'parameters': None
    #     }
    #     active_models.append(model)

    clients = [ModelClient(m, settings) for m in active_models]

    titles = [m["title"] for m in active_models]
    logging.getLogger(__name__).info('Loaded models: ' + ', '.join(titles))


def run_active_models(model_input):
    for client in clients:
        client.run(model_input)
