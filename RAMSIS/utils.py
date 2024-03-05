# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Various utility functions
"""

import collections
import functools

from ramsis.utils.error import Error
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


class RamsisError(Error):
    """Base RAMSIS exception ({})."""


Message = collections.namedtuple(
    'StatusMessage', ['status', 'status_code', 'data', 'info'])


class SynchronousThread:
    """
    Class for managing db tasks which should be done synchronously
    but in a thread in threadpool. Tasks which involve loading the forecast
    or project are required to finish before the next
    one is started as the same object cannot be loaded by different
    sessions in sqlalchemy.
    """

    def __init__(self):
        self.thread_reserved = False
        self.model_runs = 0
        self.model_runs_count = 0

    def reserve_thread(self):
        self.thread_reserved = True

    def release_thread(self):
        self.thread_reserved = False

    def is_reserved(self):
        return self.thread_reserved
