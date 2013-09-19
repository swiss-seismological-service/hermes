# -*- encoding: utf-8 -*-
"""
Main file

The Main file sets up the user interface and bootstraps the application

"""
import sys
from PyQt4 import QtGui
from ui.mainwindow import MainWindow
from atlas import Atlas


def main():
    """
    Launches Atlas i.s.

    Creates the Atlas top level object and passes control to it.

    """
    atlas = Atlas()
    atlas.launch()


if __name__ == "__main__":
    main()