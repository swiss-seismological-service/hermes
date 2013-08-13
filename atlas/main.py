# -*- encoding: utf-8 -*-
"""
Main file

The Main file sets up the user interface and bootstraps the application

"""
import sys
from PyQt4 import QtGui
from ui.mainwindow import MainWindow
from atlasengine import AtlasEngine


def main():
    """Creates and launches the user interface"""

    # Start the engine
    engine = AtlasEngine()

    # Create and start the user interface
    app = QtGui.QApplication(sys.argv)
    window = MainWindow(engine)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()