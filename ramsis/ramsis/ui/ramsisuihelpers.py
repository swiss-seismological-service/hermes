# -*- encoding: utf-8 -*-
"""
GUI helpers

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from dateutil.tz import tzlocal, tzutc
from PyQt4 import QtGui
from PyQt4.QtCore import QDateTime


class DateDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super(DateDialog, self).__init__(parent)

        layout = QtGui.QVBoxLayout(self)

        # info text
        self.label = QtGui.QLabel(
            text='The file appears to contain relative dates.\n'
                 'Please specify a reference date.')
        layout.addWidget(self.label)

        # nice widget for editing the date
        self.datetime = QtGui.QDateTimeEdit(self)
        self.datetime.setCalendarPopup(True)
        self.datetime.setDisplayFormat('yyyy-MM-dd hh:mm:ss')
        self.datetime.setDateTime(QDateTime.currentDateTime())
        layout.addWidget(self.datetime)

        # OK and Cancel buttons
        self.buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok |
                                              QtGui.QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout.addWidget(self.buttons)
        self.setLayout(layout)

    # get current date and time from the dialog
    def date_time(self):
        return self.datetime.dateTime()

    # static method to create the dialog and return (date, time, accepted)
    @staticmethod
    def get_date_time(parent=None):
        dialog = DateDialog(parent)
        result = dialog.exec_()
        date = dialog.date_time()
        return date.toPyDateTime(), result == QtGui.QDialog.Accepted


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
