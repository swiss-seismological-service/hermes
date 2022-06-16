# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Toplevel application object

Bootstraps the application and ties everything together (more specifically
the GUI and the Ramsis core application).

"""

import os
import logging
import signal
import sys

from PyQt5 import QtCore
from PyQt5.QtCore import QStandardPaths
from PyQt5.QtWidgets import QApplication

from RAMSIS import __version__
from RAMSIS.ui.ramsisgui import RamsisGui
from RAMSIS.core.controller import Controller, LaunchMode
from RAMSIS.db import store, AppSettings


class Application(QtCore.QObject):
    """
    Top level application object

    Bootstraps the application and emits the app_launched signal as soon as
    the program is ready. At that point the ui has been initialized, signals
    are connected and the event loop has become active).

    This top level application object also takes ownership of the main
    application components, i.e. the core, settings and the application user
    interface

    """

    #: Signal emitted after the app has completed launching
    app_launched = QtCore.pyqtSignal()

    def __init__(self, args):
        """
        Instantiates the Ramsis core and the Qt app (run loop) and
        wires the GUI.

        :param args: command line arguments that were provided by the user

        """
        super().__init__()
        self.thread().setObjectName('Main')
        # Setup the logger
        self.logger = logging.getLogger(__name__)
        self.logger.info('Launching RAMSIS v' + __version__)
        # Instantiate the appropriate Qt app object
        self.has_gui = not args.no_gui
        if self.has_gui:
            self.qt_app = QApplication(sys.argv)
        else:
            self.qt_app = QtCore.QCoreApplication(sys.argv)
        # Register some general app information
        self.qt_app.setApplicationName('Ramsis')
        self.qt_app.setOrganizationDomain('seismo.ethz.ch')
        self.qt_app.setApplicationVersion(__version__)
        self.qt_app.setOrganizationName('SED')
        # Load application settings
        locations = QStandardPaths.\
            standardLocations(QStandardPaths.AppConfigLocation)
        paths = (os.path.join(loc, 'settings.yml') for loc in locations)
        settings_file = next((p for p in paths if os.path.isfile(p) or
                              os.path.islink(p)),
                             'settings.yml')
        print("settings file ###############", settings_file)
        if os.path.islink(settings_file):
            settings_file = os.readlink(settings_file)
        self.app_settings = AppSettings(settings_file)
        # Enable Ctrl-C
        signal.signal(signal.SIGINT, self._on_sigint)
        # Once the Qt event loop is running, we need a timer to periodically
        # run the Python interpreter so it can process Ctrl-C signals
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(lambda: None)
        self.timer.start(500)
        # Launch core
        launch_mode = LaunchMode(self.app_settings['launch_mode'])
        self.ramsis_core = Controller(self, launch_mode, store)
        if self.has_gui:
            self.gui = RamsisGui(self)
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
            self.gui.show()
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
        sys.exit(code)
