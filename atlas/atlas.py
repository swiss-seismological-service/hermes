# -*- encoding: utf-8 -*-
"""
Toplevel application object

Bootstraps the application and ties everything together (more specifically
the GUI and the Atlas core application).
    
"""

import sys
from PyQt4 import QtGui
from ui.mainwindowcontroller import MainWindowController
from atlascore import AtlasCore


class Atlas(object):
    """
    Top level application object

    """

    def launch(self):
        """
        Launches Atlas i.s.

        Instantiates the Atlas core and connects the GUI. This function does
        not return until the program quits.

        """

        # Start the core application
        atlas_core = AtlasCore()

        # Create and start the user interface
        app = QtGui.QApplication(sys.argv)
        window = MainWindowController(atlas_core)
        window.show()
        sys.exit(app.exec_())