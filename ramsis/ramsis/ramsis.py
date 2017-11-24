# -*- encoding: utf-8 -*-
"""
Toplevel application object

Bootstraps the application and ties everything together (more specifically
the GUI and the Ramsis core application).

"""

import sys
import os
import logging
import signal

from PyQt4 import QtGui, QtCore

from qgis.core import QgsApplication

from .ui.mainwindow.window import MainWindow
from .core.controller import Controller
from .ramsissettings import AppSettings


VERSION = '0.1 "Bug Infested Alpha"'

# Initialize QGIS
prefix_path = os.environ.get('QGIS_PREFIX_PATH')
if not prefix_path:
    logging.getLogger(__name__).warn('QGIS prefix path is not set')
QgsApplication.setPrefixPath(prefix_path, True)


class Ramsis(QtCore.QObject):
    """
    Top level application object

    Emits the app_launched signal as soon as the program has started (i.e.
    as soon as the event loop becomes active)

    """

    # Signals
    app_launched = QtCore.pyqtSignal()

    def __init__(self, args):
        """
        Instantiates the Ramsis core and the Qt app (run loop) and
        wires the GUI.

        :param args: command line arguments that were provided by the user
        :type args: dict

        """
        super(Ramsis, self).__init__()
        self.thread().setObjectName('Main')
        # Setup the logger
        self.logger = logging.getLogger(__name__)
        self.logger.info('Launching RAMSIS v' + VERSION)
        # Instantiate the appropriate Qt app object
        self.has_gui = not args.no_gui
        if self.has_gui:
            QtGui.QApplication.setStyle(
                QtGui.QStyleFactory.create('Cleanlooks'))
            self.qt_app = QtGui.QApplication(sys.argv)
            QgsApplication.initQgis()
        else:
            self.qt_app = QtCore.QCoreApplication(sys.argv)
        # Register some general app information
        self.qt_app.setApplicationName('Ramsis')
        self.qt_app.setOrganizationDomain('seismo.ethz.ch')
        self.qt_app.setApplicationVersion(VERSION)
        self.qt_app.setOrganizationName('SED')
        # Load settings
        path = args.config if args.config else 'ramsis.ini'
        settings_file = os.path.abspath(path)
        self.app_settings = AppSettings(settings_file)
        # Enable Ctrl-C
        signal.signal(signal.SIGINT, self._on_sigint)
        # Once the Qt event loop is running, we need a timer to periodically
        # run the Python interpreter so it can process Ctrl-C signals
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(lambda: None)
        self.timer.start(500)
        # Launch core
        self.ramsis_core = Controller(settings=self.app_settings)
        if self.has_gui:
            self.main_window = MainWindow(self)
        self.app_launched.connect(self.on_app_launched)

    def run(self):
        """
        Launches and runs Ramsis i.s.

        The app launch signal will be delivered as soon as the event loop
        starts (which happens in exec_(). This function does not return until
        the app exits.

        """
        self.logger.info('RAMSIS is ready')

        if self.has_gui:
            self.main_window.show()
        # noinspection PyCallByClass
        QtCore.QTimer.singleShot(0, self._emit_app_launched)
        self._exit(self.qt_app.exec_())

    def on_app_launched(self):
        pass

    def _emit_app_launched(self):
        self.app_launched.emit()

    def _on_sigint(self, signalnum, frame):
        self._exit(0)

    def _exit(self, code):
        if self.has_gui:
            QgsApplication.exitQgis()
        sys.exit(code)
