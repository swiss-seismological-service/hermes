# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Toplevel application object

Bootstraps the application and ties everything together (more specifically
the GUI and the Ramsis core application).

"""

import collections
import operator
import os
import logging
import signal
import sys
import yaml

from functools import reduce

from PyQt5 import QtCore
from PyQt5.QtCore import QStandardPaths
from PyQt5.QtWidgets import QApplication

from RAMSIS import __version__
from RAMSIS.ui.ramsisgui import RamsisGui
from RAMSIS.core.controller import Controller, LaunchMode


class AppSettings:
    """
    Global application settings.

    To access settings through this class.

    """

    def __init__(self, settings_file=None):
        """
        Load either the default settings or, if a file name is
        provided, specific settings from that file.

        """
        self._settings_file = settings_file
        self._logger = logging.getLogger(__name__)
        if settings_file is None:
            settings_file = 'settings.yml'

        self._logger.info('Loading settings from ' + settings_file)
        with open(settings_file, 'r') as f:
            self.settings = yaml.full_load(f.read())

    def all(self):
        """ Return all settings as a flat dict: {'section/key': value} """
        def flatten(d, parent_key='', sep='/'):
            items = []
            for k, v in d.items():
                new_key = parent_key + sep + k if parent_key else k
                if isinstance(v, collections.MutableMapping):
                    items.extend(flatten(v, new_key, sep=sep).items())
                else:
                    items.append((new_key, v))
            return dict(items)

        return flatten(self.settings)

    def __getitem__(self, key):
        return reduce(operator.getitem, key.split('/'), self.settings)

    def __setitem__(self, key, value):
        keys = key.split('/')
        if len(keys) > 1:
            leaf_node = reduce(operator.getitem, keys[:-1], self.settings)
        else:
            leaf_node = self.settings
        leaf_node[keys[-1]] = value


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
        self.ramsis_core = Controller(self, launch_mode)
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
