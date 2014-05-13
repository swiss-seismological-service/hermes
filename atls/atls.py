# -*- encoding: utf-8 -*-
"""
Toplevel application object

Bootstraps the application and ties everything together (more specifically
the GUI and the Atls core application).
    
"""

import sys
import logging
from PyQt4 import QtGui, QtCore
from ui.mainwindow import MainWindow
from atlscore import AtlsCore
from atlssettings import AppSettings
import tools


class Atls(QtCore.QObject):
    """
    Top level application object

    Emits the app_launched signal as soon as the program has started (i.e.
    as soon as the event loop becomes active)

    """

    # Signals
    app_launched = QtCore.pyqtSignal()

    def __init__(self, args, logger):
        """
        Instantiates the Atls core and the Qt app (run loop) and
        wires the GUI.

        :param args: command line arguments that were provided by the user
        :type args: dict

        """
        super(Atls, self).__init__()
        self.app_settings = AppSettings()
        # Register basic app info
        self.qt_app = QtGui.QApplication(sys.argv, GUIenabled=(not args.nogui))
        self.qt_app.setApplicationName('Atls')
        self.qt_app.setOrganizationDomain('seismo.ethz.ch')
        self.qt_app.setApplicationVersion('0.1')
        self.qt_app.setOrganizationName('SED')
        # Setup the root logger
        self.logger = self._create_root_logger(args.verbosity)
        # Launch core
        self.atls_core = AtlsCore(settings=self.app_settings)
        if not args.nogui:
            self.main_window = MainWindow(self)
        self.app_launched.connect(self.on_app_launched)

    def run(self):
        """
        Launches and runs Atls i.s.

        The app launch signal will be delivered as soon as the event loop
        starts (which happens in exec_(). This function does not return until
        the app exits.

        """
        self.logger.info('Atls is starting')

        self.main_window.show()
        QtCore.QTimer.singleShot(0, self._emit_app_launched)
        sys.exit(self.qt_app.exec_())

    def on_app_launched(self):
        pass

    def _emit_app_launched(self):
        self.app_launched.emit()

    def _create_root_logger(self, verbosity):
        """
        Configures and returns the root logger.

        All loggers in submodules will automatically become children of the root
        logger and inherit some of the properties.

        """
        lvl_lookup = {
            0: logging.ERROR,
            1: logging.NOTICE,
            2: logging.INFO,
            3: logging.DEBUG
        }
        # Create a logger that can handle 'NOTICE' levels
        logging.setLoggerClass(tools.AtlsLogger)
        logging.NOTICE = 25
        logging.addLevelName(logging.NOTICE, 'NOTICE')
        logger = logging.getLogger('ATLS')
        logger.setLevel(lvl_lookup[verbosity])
        formatter = logging.Formatter('%(asctime)s %(levelname)s: '
                                      '[%(name)s] %(message)s')
        # ...setup console logging
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        return logger