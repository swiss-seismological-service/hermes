# -*- encoding: utf-8 -*-
"""
Controller module for the main window

"""

from PyQt4 import QtGui
from views.uimainwindow import Ui_MainWindow
from models.catalogmodel import CatalogModel
import os


# Create a class for our main window
class MainWindow(QtGui.QMainWindow):
    """Class that manages the main application window"""

    def __init__(self, engine):
        QtGui.QMainWindow.__init__(self)

        # A reference to the engine (business logic)
        self.engine = engine

        # Setup the user interface
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.statusBar().showMessage('Ready')

        # Hook up the menu
        self.ui.action_Import.triggered.connect(self.import_seismic_catalog)
        self.ui.actionView_Data.triggered.connect(self.view_catalog_data)

    # menu actions

    def import_seismic_catalog(self):
        home = os.path.expanduser("~")
        path = QtGui.QFileDialog.getOpenFileName(self, 'Open catalog file', home)

        if path:
            self.statusBar().showMessage('Importing catalog...')
            self.engine.event_history.import_from_csv(path)
            self.statusBar().showMessage('Ready')

    def view_catalog_data(self):
        self.table_view = QtGui.QTableView()
        model = CatalogModel(self.engine.event_history)
        self.table_view.setModel(model)
        self.table_view.show()
        pass