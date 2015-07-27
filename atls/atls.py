# -*- encoding: utf-8 -*-
"""
Toplevel application object

Bootstraps the application and ties everything together (more specifically
the GUI and the Atls core application).

"""

import sys
import os
import logging
import signal

from PyQt4 import QtGui, QtCore

from qgis.core import QgsApplication

from ui.mainwindow import MainWindow
from core.controller import Controller
from atlssettings import AppSettings


VERSION = '0.1 "Bug Infested Alpha"'

# Initialize QGIS
prefix_path = '/usr/local/Cellar/qgis-26/2.6.1/QGIS.app/Contents/MacOS'
QgsApplication.setPrefixPath(prefix_path, True)


class Atls(QtCore.QObject):
    """
    Top level application object

    Emits the app_launched signal as soon as the program has started (i.e.
    as soon as the event loop becomes active)

    """

    # Signals
    app_launched = QtCore.pyqtSignal()

    def __init__(self, args):
        """
        Instantiates the Atls core and the Qt app (run loop) and
        wires the GUI.

        :param args: command line arguments that were provided by the user
        :type args: dict

        """
        super(Atls, self).__init__()
        self.thread().setObjectName('Main')
        # Setup the logger
        self.logger = logging.getLogger(__name__)
        self.logger.info('Launching ATLS v' + VERSION)
        # Instantiate the appropriate Qt app object
        self.has_gui = not args.no_gui
        if self.has_gui:
            self.qt_app = QtGui.QApplication(sys.argv)
            QgsApplication.initQgis()
        else:
            self.qt_app = QtCore.QCoreApplication(sys.argv)
        # Register some general app information
        self.qt_app.setApplicationName('Atls')
        self.qt_app.setOrganizationDomain('seismo.ethz.ch')
        self.qt_app.setApplicationVersion(VERSION)
        self.qt_app.setOrganizationName('SED')
        # We expect a settings file when launching without GUI
        if self.has_gui:
            self.app_settings = AppSettings()
        else:
            settings_file = os.path.abspath(args.config)
            self.app_settings = AppSettings(settings_file)
            # reenable Ctrl-C
            signal.signal(signal.SIGINT, signal.SIG_DFL)
        # Launch core
        self.atls_core = Controller(settings=self.app_settings)
        if self.has_gui:
            self.main_window = MainWindow(self)
        self.app_launched.connect(self.on_app_launched)

    def run(self):
        """
        Launches and runs Atls i.s.

        The app launch signal will be delivered as soon as the event loop
        starts (which happens in exec_(). This function does not return until
        the app exits.

        """
        self.logger.info('ATLS is ready')

        if self.has_gui:
            self.main_window.show()
        QtCore.QTimer.singleShot(0, self._emit_app_launched)
        sys.exit(self.qt_app.exec_())
        if self.has_gui:
            QgsApplication.exitQgis()

    def on_app_launched(self):
        # Check if we should load a project on launch
        project = self.app_settings.value('project')
        open_last = self.app_settings.value('open_last_project', type=bool)
        if not project and open_last:
            self.logger.warn('open_last_project is not currently implemented')
            pass  # TODO: implement loading the last project
        if project:
            path = os.path.abspath(project)
            self.atls_core.open_project(path)
        if not self.has_gui:
            self.atls_core.start_simulation()

    def _emit_app_launched(self):
        self.app_launched.emit()
