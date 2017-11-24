# -*- encoding: utf-8 -*-
"""
Controller class for the simulation control window

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import os
import logging
from PyQt4 import QtGui, uic

from core.simulator import SimulatorState
from .ramsisuihelpers import pyqt_local_to_utc_ua, utc_to_local

ui_path = os.path.dirname(__file__)
SIM_WINDOW_PATH = os.path.join(ui_path, 'views', 'simulationwindow.ui')
Ui_SimulationWindow = uic.loadUiType(SIM_WINDOW_PATH)[0]


class SimulationWindow(QtGui.QDialog):

    def __init__(self, ramsis_core, **kwargs):
        QtGui.QMainWindow.__init__(self, **kwargs)
        self.logger = logging.getLogger(__name__)

        # References
        self.ramsis_core = ramsis_core

        # Setup the user interface
        self.ui = Ui_SimulationWindow()
        self.ui.setupUi(self)

        # Hook up buttons
        self.ui.startButton.clicked.connect(self.action_start_simulation)
        self.ui.stopButton.clicked.connect(self.action_stop_simulation)
        self.ui.pauseButton.clicked.connect(self.action_pause_simulation)
        self.ui.afapCheckBox.stateChanged.connect(self.on_afap_state_change)

        # Hook up signals from the core
        self.ramsis_core.simulator.state_changed.\
            connect(self.on_sim_state_change)
        self.ramsis_core.project_loaded.connect(self.on_project_load)

        project = ramsis_core.project
        if project:
            local = utc_to_local(project.start_date)
            self.ui.startTimeEdit.setDateTime(local)
            local = utc_to_local(project.end_date)
            self.ui.endTimeEdit.setDateTime(local)

    def update_controls(self):
        afap = self.ui.afapCheckBox.isChecked()
        if not self.ramsis_core.project:
            self.ui.startButton.setEnabled(False)
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(False)
            self.ui.speedSpinBox.setEnabled(not afap)
            self.ui.afapCheckBox.setEnabled(True)
            return
        sim_state = self.ramsis_core.simulator.state
        if sim_state == SimulatorState.RUNNING:
            self.ui.startButton.setEnabled(False)
            self.ui.pauseButton.setEnabled(True)
            self.ui.stopButton.setEnabled(True)
            self.ui.speedSpinBox.setEnabled(False)
            self.ui.afapCheckBox.setEnabled(False)
        elif sim_state == SimulatorState.PAUSED:
            self.ui.startButton.setEnabled(True)
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(True)
            self.ui.speedSpinBox.setEnabled(not afap)
            self.ui.afapCheckBox.setEnabled(True)
        else:
            # STOPPED
            self.ui.startButton.setEnabled(True)
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(False)
            self.ui.speedSpinBox.setEnabled(not afap)
            self.ui.afapCheckBox.setEnabled(True)

    # Actions

    def action_start_simulation(self):
        # Convert from QDateTime to Python datetime
        start_time = pyqt_local_to_utc_ua(self.ui.startTimeEdit.dateTime())
        end_time = pyqt_local_to_utc_ua(self.ui.endTimeEdit.dateTime())

        time_range = (start_time, end_time)
        speed = -1 if self.ui.afapCheckBox.isChecked() \
            else self.ui.speedSpinBox.value()
        self.ramsis_core.start(time_range, speed)

    def action_pause_simulation(self):
        self.ramsis_core.pause()

    def action_stop_simulation(self):
        self.ramsis_core.stop()

    # Observed Signals

    def on_sim_state_change(self, _):
        self.update_controls()

    def on_project_load(self, project):
        local = utc_to_local(project.start_date)
        self.ui.startTimeEdit.setDateTime(local)
        local = utc_to_local(project.end_date)
        self.ui.endTimeEdit.setDateTime(local)
        # Make sure we get updated on project changes
        project.will_close.connect(self.on_project_will_close)
        self.update_controls()

    def on_project_will_close(self, project):
        self.update_controls()

    def on_afap_state_change(self):
        self.update_controls()

    # TODO: remove, we're not the main window anymore
    # Status Updates
    #
    # def update_status(self):
    #     """
    #     Updates the status message in the status bar.
    #
    #     """
    #     if self.project is None:
    #         self.ui.coreStatusLabel.setText('Idle')
    #         self.ui.projectTimeLabel.setText('-')
    #         self.ui.lastEventLabel.setText('-')
    #         self.ui.nextForecastLabel.setText('-')
    #         return
    #
    #     core = self.ramsis_core
    #     time = self.project.project_time
    #     t_forecast = core.engine.t_next_forecast
    #     speed = self.ramsis_core.simulator.speed
    #     if core.simulator.state == SimulatorState.RUNNING:
    #         event = self.project.seismic_catalog.latest_event(time)
    #         status = 'Simulating at ' + str(speed) + 'x'
    #         if core.forecast_job.busy:
    #             status += ' - Computing Forecast'
    #         self.ui.coreStatusLabel.setText(status)
    #         self.ui.projectTimeLabel.setText(time.ctime())
    #         self.ui.lastEventLabel.setText(str(event))
    #         self.ui.nextForecastLabel.setText(str(t_forecast.ctime()))
    #     elif core.simulator.state == SimulatorState.PAUSED:
    #         event = self.project.seismic_catalog.latest_event(time)
    #         self.ui.coreStatusLabel.setText('Paused')
    #         self.ui.projectTimeLabel.setText(time.ctime())
    #         self.ui.lastEventLabel.setText(str(event))
    #         self.ui.nextForecastLabel.setText(str(t_forecast.ctime()))
    #     else:
    #         self.ui.coreStatusLabel.setText('Idle')
    #         self.ui.projectTimeLabel.setText(time.ctime())
    #         self.ui.lastEventLabel.setText('-')
    #         self.ui.nextForecastLabel.setText('-')
