# -*- encoding: utf-8 -*-
"""
Controller module for the main window

"""

from PyQt4 import QtGui
from views.uimainwindow import Ui_MainWindow
from models.catalogmodel import CatalogModel
from datetime import datetime
import datamodel.seismiceventhistory
import os

import numpy as np


# Create a class for our main window
class MainWindow(QtGui.QMainWindow):
    """
    Class that manages the main application window

    """

    def __init__(self, atlas_core):
        QtGui.QMainWindow.__init__(self)

        # A reference to the engine (business logic)
        self.atlas_core = atlas_core

        # Setup the user interface
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.statusBar().showMessage('Ready')

        # Hook up the menu
        self.ui.action_Import.triggered.connect(self.import_seismic_catalog)
        self.ui.actionView_Data.triggered.connect(self.view_catalog_data)

        self._replot_catalog()

    # menu actions

    def import_seismic_catalog(self):
        home = os.path.expanduser("~")
        path = QtGui.QFileDialog.getOpenFileName(self, 'Open catalog file', home)

        if path:
            self.statusBar().showMessage('Importing catalog...')
            self.atlas_core.event_history.import_from_csv(path)
            self.statusBar().showMessage('Ready')
            self.ui.label.setText('Catalog: ' + path)
            self._replot_catalog()

    def view_catalog_data(self):
        self.table_view = QtGui.QTableView()
        model = CatalogModel(self.engine.event_history)
        self.table_view.setModel(model)
        self.table_view.show()


    def update_plots(self, time=None):
        """
        Updates all plots

        :param time: if not none, the current time is assumed to be *time*

        """

    # Plot Helpers



    def _replot_catalog(self, update=False, max_time=None):
        """Plot the data in the catalog

        :param max_time: if not None, plot catalog up to max_time only
        :param update: If false (default) the entire catalog is replotted
        :type update: bool

        """
        if update:
            pass
        else:
            epoch = datetime(1970, 1, 1)
            events = self.atlas_core.event_history
            data = [((e.date_time - epoch).total_seconds(), e.magnitude)
                    for e in events]
            self.ui.catalog_plot.plot.setData(pos=data)