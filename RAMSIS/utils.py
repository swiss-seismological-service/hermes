# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Various utility functions

"""
import abc
import functools
from PyQt5.QtCore import QTimer, QObject, QDateTime
from sqlalchemy import event


def datetime_to_qdatetime(dt):
    """
    Convert a :py:class:`datetime.datetime` object into a corresponding
    :py:class:`PyQt5.QtCore.QDateTime` object.

    :param dt: Datetime to be converted
    :type dt: :py:class:`datetime.datetime`
    
    :rtype: :py:class:`PyQt5.QtCore.QDateTime`
    """
    return QDateTime.fromMSecsSinceEpoch(int(dt.timestamp() * 1000))


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


class QtABCMeta(type(QObject), abc.ABCMeta):
    pass
