# -*- encoding: utf-8 -*-
"""
Toplevel application object

Bootstraps the application and ties everything together (more specifically
the GUI and the Atlas core application).
    
"""

import sys
import logging
from PyQt4 import QtGui, QtCore
from ui.mainwindowcontroller import MainWindowController
from atlascore import AtlasCore


class Atlas(QtCore.QObject):
    """
    Top level application object

    Emits the app_launched signal as soon as the program has started (i.e.
    as soon as the event loop becomes active)

    """

    # Signals
    app_launched = QtCore.pyqtSignal()

    def __init__(self):
        """
        Instantiates the Atlas core and the Qt app (run loop) and
        wires the GUI.

        """
        super(Atlas, self).__init__()

        self.qt_app = QtGui.QApplication(sys.argv)
        self.qt_app.setApplicationName('Atlas')
        self.qt_app.setOrganizationDomain('seismo.ethz.ch')
        self.qt_app.setApplicationVersion('0.1')
        self.qt_app.setOrganizationName('SED')

        self.atlas_core = AtlasCore()
        self.main_window = MainWindowController(self)
        self.app_launched.connect(self.on_app_launched)

        # Configure Logging
        ch = logging.StreamHandler()        # Log to console
        formatter = logging.Formatter('%(asctime)s %(levelname)s: '
                                      '[%(name)s] %(message)s')
        ch.setFormatter(formatter)
        self.logger = logging.getLogger()
        self.logger.addHandler(ch)
        self.logger.setLevel(logging.INFO)

    def run(self):
        """
        Launches and runs Atlas i.s.

        The app launch signal will be delivered as soon as the event loop
        starts (which happens in exec_(). This function does not return until
        the app exits.

        """
        self.logger.info('Atlas is starting')

        self.main_window.show()
        QtCore.QTimer.singleShot(0, self._emit_app_launched)
        sys.exit(self.qt_app.exec_())

    def on_app_launched(self):
        """
        Start the core after the app has finished launching and the event loop
        is running

        """

        self.atlas_core.start()

    def _emit_app_launched(self):
        self.app_launched.emit()