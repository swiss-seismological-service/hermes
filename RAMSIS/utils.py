# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Various utility functions
"""

import functools

from ramsis.datamodel import EStatus


def reset_forecast(forecast):
    forecast.status = EStatus.PENDING
    for run in forecast.runs:
        run.status = EStatus.PENDING
    return forecast


def rsetattr(obj, attr, val):
    """
    Recursive setattr variant

    A plugin replacement for the built in `setattr` that allows to set nested
    attributes with dot separation:

        rsetattr(employee, 'address.street.number', '5a')

    """
    pre, _, post = attr.rpartition('.')
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)


def rgetattr(obj, attr, *args):
    """
    Recursive getattr variant

    A plugin replacement for the built in `getattr` that allows to get nested
    attributes with dot separation:

        street_number = rgetattr(employee, 'address.street.number')

    """
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)
    return functools.reduce(_getattr, [obj] + attr.split('.'))
