# -*- encoding: utf-8 -*-
"""
Controller module for the main window

"""

from PyQt4 import QtGui
from views.ui_mainwindow import Ui_MainWindow
from models.catalogmodel import CatalogModel
from datetime import datetime
from atlascore import AtlasCore, AtlasCoreState
import datamodel.seismiceventhistory
import os

import numpy as np


# Create a class for our main window
class MainWindowController(QtGui.QMainWindow):
    """
    Class that manages the main application window

    """

    def __init__(self, atlas_core):
        QtGui.QMainWindow.__init__(self)

        # Project time as displayed in status bar
        self.displayed_project_time = None

        # A reference to the engine (business logic)
        self.atlas_core = atlas_core

        # Setup the user interface
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Hook up the menu
        self.ui.action_Import.triggered.connect(self.import_seismic_catalog)
        self.ui.actionView_Data.triggered.connect(self.view_catalog_data)
        self.ui.actionStart_Simulation.triggered.connect(self.start_simulation)
        self.ui.actionPause_Simulation.triggered.connect(self.pause_simulation)
        self.ui.actionStop_Simulation.triggered.connect(self.stop_simulation)
        # ... buttons
        self.ui.startButton.pressed.connect(self.start_forecast)
        self.ui.pauseButton.pressed.connect(self.pause_forecast)
        self.ui.stopButton.pressed.connect(self.stop_forecast)
        # ... other controls
        self.ui.simulationCheckBox.stateChanged.connect(self.sim_state_changed)
        self.ui.speedBox.valueChanged.connect(self.sim_speed_changed)


        # Hook up model change signals
        self.atlas_core.state_changed.connect(self.handle_core_state_change)
        self.atlas_core.event_history.history_changed.connect(self.handle_history_change)
        self.atlas_core.project_time_changed.connect(self.handle_project_time_change)

        self._replot_catalog()
        self.update_status()
        self.update_controls()

    # Menu Actions

    def import_seismic_catalog(self):
        home = os.path.expanduser("~")
        path = QtGui.QFileDialog.getOpenFileName(self, 'Open catalog file', home)

        if path:
            self.atlas_core.event_history.import_from_csv(path)
            self.statusBar().showMessage('Ready')
            self.ui.label.setText('Catalog: ' + path)

    def view_catalog_data(self):
        self.table_view = QtGui.QTableView()
        model = CatalogModel(self.engine.event_history)
        self.table_view.setModel(model)
        self.table_view.show()

    # ... Simulation

    def start_simulation(self):
        self._clear_plots()
        speed = self.ui.speedBox.value()
        self.atlas_core.simulator.speed = speed
        self.atlas_core.start_simulation()

    def pause_simulation(self):
        self.atlas_core.pause_simulation()

    def stop_simulation(self):
        self.atlas_core.stop_simulation()
        self._replot_catalog()


    # Button Actions

    def start_forecast(self):
        if self.ui.simulationCheckBox.isChecked():
            self.start_simulation()
        else:
            pass

    def pause_forecast(self):
        if self.ui.simulationCheckBox.isChecked():
            self.pause_simulation()
        else:
            pass

    def stop_forecast(self):
        if self.ui.simulationCheckBox.isChecked():
            self.stop_simulation()
        else:
            pass

    def sim_state_changed(self):
        pass

    def sim_speed_changed(self):
        speed = self.ui.speedBox.value()
        self.atlas_core.simulator.speed = speed


    # Qt Signal Slots

    def handle_history_change(self, dict):
        time = dict.get('simulation_time')
        if time is None:
            self._replot_catalog()
        else:
            self._replot_catalog(update=True, max_time=time)
        self.update_status()

    def handle_core_state_change(self, state):
        self.update_controls()
        if self.atlas_core.state == AtlasCoreState.SIMULATING:
            self.displayed_project_time = self.atlas_core.project_time
        self.update_status()

    def handle_project_time_change(self, time):
        self.displayed_project_time = time
        self.update_status()

    # Control Updates

    def update_controls(self):
        state = self.atlas_core.state
        if state == AtlasCoreState.SIMULATING:
            self.ui.simulationCheckBox.setEnabled(False)
            self.ui.startButton.setEnabled(False)
            self.ui.pauseButton.setEnabled(True)
            self.ui.stopButton.setEnabled(True)
            self.ui.actionStart_Simulation.setEnabled(False)
            self.ui.actionPause_Simulation.setEnabled(True)
            self.ui.actionStop_Simulation.setEnabled(True)
        elif state == AtlasCoreState.PAUSED:
            self.ui.simulationCheckBox.setEnabled(False)
            self.ui.startButton.setEnabled(True)
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(True)
            self.ui.actionStart_Simulation.setEnabled(True)
            self.ui.actionPause_Simulation.setEnabled(False)
            self.ui.actionStop_Simulation.setEnabled(True)
        elif state == AtlasCoreState.FORECASTING:
            self.ui.simulationCheckBox.setEnabled(False)
            self.ui.startButton.setEnabled(False)
            self.ui.pauseButton.setEnabled(True)
            self.ui.stopButton.setEnabled(True)
            self.ui.actionStart_Simulation.setEnabled(False)
            self.ui.actionPause_Simulation.setEnabled(True)
            self.ui.actionStop_Simulation.setEnabled(True)
        else:
            # IDLE
            self.ui.simulationCheckBox.setEnabled(True)
            self.ui.startButton.setEnabled(True)
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(False)
            self.ui.actionStart_Simulation.setEnabled(True)
            self.ui.actionPause_Simulation.setEnabled(False)
            self.ui.actionStop_Simulation.setEnabled(False)

    # Status Updates

    def update_status(self):
        """
        Updates the status message in the status bar.

        """
        core = self.atlas_core
        time = core.project_time
        speed = self.atlas_core.simulator.speed
        if core.state == AtlasCoreState.SIMULATING:
            event = self.atlas_core.event_history.latest_event(time)
            self.ui.coreStatusLabel.setText('Simulating at ' + str(speed) + 'x')
            self.ui.projectTimeLabel.setText(self.displayed_project_time.ctime())
            self.ui.lastEventLabel.setText(str(event))
        elif core.state == AtlasCoreState.FORECASTING:
            event = self.atlas_core.event_history.latest_event()
            self.ui.coreStatusLabel.setText('Forecasting')
            self.ui.projectTimeLabel.setText(str(self.displayed_project_time))
            self.ui.lastEventLabel.setText(str(event))
        elif core.state == AtlasCoreState.PAUSED:
            event = self.atlas_core.event_history.latest_event(time)
            self.ui.coreStatusLabel.setText('Paused')
            self.ui.projectTimeLabel.setText(str(self.displayed_project_time))
            self.ui.lastEventLabel.setText(str(event))
        else:
            num_events = len(core.event_history)
            self.ui.coreStatusLabel.setText('Idle')
            self.ui.projectTimeLabel.setText('-')
            self.ui.lastEventLabel.setText('-')
            self.statusBar().showMessage(str(num_events) +
                                         ' events in catalog')

    # Plot Helpers

    def _clear_plots(self):
        self.ui.catalog_plot.plot.setData()

    def _replot_catalog(self, update=False, max_time=None):
        """Plot the data in the catalog

        :param max_time: if not None, plot catalog up to max_time only
        :param update: If false (default) the entire catalog is replotted
        :type update: bool

        """
        epoch = datetime(1970, 1, 1)
        events = self.atlas_core.event_history
        if max_time:
            data = [((e.date_time - epoch).total_seconds(), e.magnitude)
                    for e in events if e.date_time < max_time]
        else:
            data = [((e.date_time - epoch).total_seconds(), e.magnitude)
                    for e in events]
        self.ui.catalog_plot.plot.setData(pos=data)