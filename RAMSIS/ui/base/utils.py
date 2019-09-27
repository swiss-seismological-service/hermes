# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
GUI helpers
"""

from dateutil.tz import tzlocal, tzutc
from PyQt5.QtCore import QDateTime



def utc_to_local(utc):
    utc = utc.replace(tzinfo=tzutc())
    return utc.astimezone(tzlocal())


def local_to_utc_ua(local):
    local = local.replace(tzinfo=tzlocal())
    local = local.astimezone(tzutc())
    return local.replace(tzinfo=None)


def pyqt_local_to_utc_ua(qdatetime):
    """
    Convert Qt local QDateTime to unaware python datetime (UTC)

    :param QDateTime qdatetime: QDateTime to convert
    :return: datetime

    """
    return local_to_utc_ua(qdatetime.toPyDateTime())
