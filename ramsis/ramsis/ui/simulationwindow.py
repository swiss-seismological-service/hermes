# -*- encoding: utf-8 -*-
"""
Controller class for the simulation control window

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import os
import logging
from PyQt4 import QtGui, uic

from core.simulator import SimulatorState

ui_path = os.path.dirname(__file__)
SIM_WINDOW_PATH = os.path.join(ui_path, 'views', 'simulationwindow.ui')
Ui_SimulationWindow = uic.loadUiType(SIM_WINDOW_PATH)[0]


class SimulationWindow(QtGui.QDialog):

    def __init__(self, ramsis_core, **kwargs):
        QtGui.QMainWindow.__init__(self, **kwargs)
        self.logger = logging.getLogger(__name__)

        # References
        self.ramsis_core = ramsis_core
        self.project = None

        # Setup the user interface
        self.ui = Ui_SimulationWindow()
        self.ui.setupUi(self)

        # Hook up buttons
        self.ui.startButton.clicked.connect(self.action_start_simulation)
        self.ui.stopButton.clicked.connect(self.action_stop_simulation)
        self.ui.pauseButton.clicked.connect(self.action_pause_simulation)

        # Hook up signals from the core
        self.ramsis_core.simulator.state_changed.\
            connect(self.on_sim_state_change)
        self.ramsis_core.project_loaded.connect(self.on_project_load)

    def update_controls(self):
        if not self.ramsis_core.project:
            self.ui.startButton.setEnabled(False)
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(False)
            return
        sim_state = self.ramsis_core.simulator.state
        if sim_state == SimulatorState.RUNNING:
            self.ui.startButton.setEnabled(False)
            self.ui.pauseButton.setEnabled(True)
            self.ui.stopButton.setEnabled(True)
        elif sim_state == SimulatorState.PAUSED:
            self.ui.startButton.setEnabled(True)
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(True)
        else:
            # STOPPED
            self.ui.startButton.setEnabled(True)
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(False)

    # Actions

    def action_start_simulation(self):
        # Convert from QDateTime to Python datetime
        start_time = self.ui.startTimeEdit.dateTime().toPyDateTime()
        end_time = self.ui.endTimeEdit.dateTime().toPyDateTime()

        time_range = (start_time, end_time)
        self.ramsis_core.start(time_range)

    def action_pause_simulation(self):
        self.ramsis_core.pause()

    def action_stop_simulation(self):
        self.ramsis_core.stop()

    # Observed Signals

    def on_sim_state_change(self, _):
        self.update_controls()
        self.update_status()

    def on_project_load(self, project):
        self.project = project

        # Make sure we get updated on project changes
        project.will_close.connect(self.on_project_will_close)
        project.project_time_changed.connect(self.on_project_time_change)
        project.seismic_catalog.catalog_changed.connect(
            self.on_seismic_catalog_change)
        project.injection_history.history_changed.connect(
            self.on_injection_history_change)
        self.update_controls()
        self.update_status()

    def on_project_will_close(self, project):
        project.will_close.disconnect(self.on_project_will_close)
        project.project_time_changed.disconnect(self.on_project_time_change)
        project.seismic_catalog.catalog_changed.disconnect(
            self.on_seismic_catalog_change)
        project.injection_history.history_changed.disconnect(
            self.on_injection_history_change)
        self.project = None
        self.update_controls()
        self.update_status()

    def on_project_time_change(self, _):
        self.update_status()

    def on_seismic_catalog_change(self, _):
        self.update_status()

    def on_injection_history_change(self, _):
        self.update_status()

    # Status Updates

    def update_status(self):
        """
        Updates the status message in the status bar.

        """
        if self.project is None:
            self.ui.coreStatusLabel.setText('Idle')
            self.ui.projectTimeLabel.setText('-')
            self.ui.lastEventLabel.setText('-')
            self.ui.nextForecastLabel.setText('-')
            return

        core = self.ramsis_core
        time = self.project.project_time
        t_forecast = core.engine.t_next_forecast
        speed = self.ramsis_core.simulator.speed
        if core.simulator.state == SimulatorState.RUNNING:
            event = self.project.seismic_catalog.latest_event(time)
            status = 'Simulating at ' + str(speed) + 'x'
            if core.forecast_job.busy:
                status += ' - Computing Forecast'
            self.ui.coreStatusLabel.setText(status)
            self.ui.projectTimeLabel.setText(time.ctime())
            self.ui.lastEventLabel.setText(str(event))
            self.ui.nextForecastLabel.setText(str(t_forecast.ctime()))
        elif core.simulator.state == SimulatorState.PAUSED:
            event = self.project.seismic_catalog.latest_event(time)
            self.ui.coreStatusLabel.setText('Paused')
            self.ui.projectTimeLabel.setText(time.ctime())
            self.ui.lastEventLabel.setText(str(event))
            self.ui.nextForecastLabel.setText(str(t_forecast.ctime()))
        else:
            self.ui.coreStatusLabel.setText('Idle')
            self.ui.projectTimeLabel.setText(time.ctime())
            self.ui.lastEventLabel.setText('-')
            self.ui.nextForecastLabel.setText('-')
