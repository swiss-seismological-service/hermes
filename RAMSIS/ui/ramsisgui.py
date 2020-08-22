# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Top level GUI class

Bootstraps the GUI and provides facilities to manage windows.

"""
import os
import logging
from PyQt5.QtCore import QEvent, QObject
from PyQt5.QtWidgets import QDateTimeEdit
from RAMSIS.utils import call_later
from RAMSIS.ui.base import controlinterface as QtIf
from RAMSIS.ui.mainwindow.window import MainWindow

FORM_PKG = 'RAMSIS.ui.views'
FORM_ROOT = ui_path = os.path.join(os.path.dirname(__file__), 'views')


class RamsisGui(QObject):
    """ RAMSIS top level GUI manager """

    def __init__(self, core):
        """
        :param core: reference to the core application

        """
        super().__init__()
        self.core = core
        self.main_window = MainWindow(core)
        self._managed_windows = set()
        self._logger = logging.getLogger(__name__)

        QtIf.register_interface(QDateTimeEdit,
                                QtIf.QDateTimeEditInterface)

    def show(self):
        self.main_window.show()

    def manage_window(self, window):
        """
        Manage a top-level window

        Takes ownership of a window and releases it when it gets closed later.

        """
        window.installEventFilter(self)
        self._managed_windows.add(window)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Close and obj in self._managed_windows:
            try:
                obj.clean_up()
            except AttributeError:
                pass
            # We need to let the event handling and thus the event loop finish
            # before we free the window by removing it from our managed windows
            call_later(self._managed_windows.discard, obj)
            return False
        else:
            return False
