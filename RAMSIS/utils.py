# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Various utility functions

"""
import functools
from PyQt5.QtCore import QTimer


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


def call_later(method, *args, **kwargs):
    """
    Invokes a method after finishing the current Qt run loop

    :param callable method: Method to invoke
    :param args: Positional args to pass to method
    :param kwargs: Keyword args to pass to method
    """
    QTimer.singleShot(0, functools.partial(method, *args, **kwargs))
