# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Controller class for the simulation control window
"""

import logging

from operator import attrgetter

from PyQt5.QtWidgets import QDialog

from RAMSIS.core.simulator import SimulatorState
from RAMSIS.ui.base.utils import pyqt_local_to_utc_ua, utc_to_local
from RAMSIS.ui.utils import UiForm


class SimulationWindow(
        QDialog, UiForm('simulationwindow.ui')):

    def __init__(self, ramsis_core, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

        # References
        self.ramsis_core = ramsis_core

        # Hook up buttons
        self.ui.startButton.clicked.connect(self.action_start_simulation)
        self.ui.stopButton.clicked.connect(self.action_stop_simulation)
        self.ui.pauseButton.clicked.connect(self.action_pause_simulation)

        # Hook up signals from the core
        self.ramsis_core.simulator.state_changed.\
            connect(self.on_sim_state_change)
        self.ramsis_core.project_loaded.connect(self.on_project_load)
        self.refresh()

    def update_controls(self):
        # TODO LH: use ui state machine
        if not self.ramsis_core.project:
            self.ui.startButton.setEnabled(False)
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(False)
            self.ui.speedSpinBox.setEnabled(False)
            return

        sim_state = self.ramsis_core.simulator.state
        if sim_state == SimulatorState.RUNNING:
            self.ui.startButton.setEnabled(False)
            self.ui.pauseButton.setEnabled(True)
            self.ui.stopButton.setEnabled(True)
            self.ui.speedSpinBox.setEnabled(False)
        elif sim_state == SimulatorState.PAUSED:
            self.ui.startButton.setEnabled(True)
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(True)
            self.ui.speedSpinBox.setEnabled(False)
        else:
            # STOPPED
            self.ui.startButton.setEnabled(True)
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(False)
            self.ui.speedSpinBox.setEnabled(True)

    def refresh(self):
        """ Refresh displayed data from model """
        project = self.ramsis_core.project
        if project:
            try:
                start = min(project.forecast_iter(),
                            key=attrgetter('starttime')).starttime
            except ValueError:
                start = project.starttime
            finally:
                start = utc_to_local(start)

            self.ui.startTimeEdit.setDateTime(start)
            if project.endtime:
                end = utc_to_local(project.endtime)
                self.ui.endTimeEdit.setDateTime(end)
            else:
                self.ui.endTimeEdit.setDateTime(start)

    # Actions

    def action_start_simulation(self):
        # Convert from QDateTime to Python datetime
        start_time = pyqt_local_to_utc_ua(self.ui.startTimeEdit.dateTime())
        end_time = pyqt_local_to_utc_ua(self.ui.endTimeEdit.dateTime())

        time_range = (start_time, end_time)
        self.ramsis_core.start(time_range, self.ui.speedSpinBox.value())

    def action_pause_simulation(self):
        self.ramsis_core.pause()

    def action_stop_simulation(self):
        self.ramsis_core.stop()

    # Observed Signals

    def on_sim_state_change(self, _):
        self.update_controls()

    def on_project_load(self, project):
        self.refresh()
        self.update_controls()
