# -*- encoding: utf-8 -*-
"""
Controller module for the main window

"""

import os
import logging

from PyQt4 import QtGui, uic
from PyQt4.QtGui import QWidget, QSizePolicy

from forecastswindow import ForecastsWindow
from settingswindow import SettingsWindow
from timelinewindow import TimelineWindow
from simulationwindow import SimulationWindow

from core.tools.eventimporter import EventImporter
import ramsisuihelpers as helpers
from viewmodels.seismicdatamodel import SeismicDataModel
from core.engine.engine import EngineState
from core.simulator import SimulatorState
from ui.views.plots import Event3DViewWidget
import numpy as np

ui_path = os.path.dirname(__file__)
SETTINGS_WINDOW_PATH = os.path.join(ui_path, 'views', 'mainwindow.ui')
Ui_MainWindow = uic.loadUiType(SETTINGS_WINDOW_PATH)[0]


# Create a class for our main window
class MainWindow(QtGui.QMainWindow):
    """
    Class that manages the main application window

    """

    def __init__(self, ramsis):
        QtGui.QMainWindow.__init__(self)
        self.logger = logging.getLogger(__name__)

        # Other windows which are lazy-loaded
        self.forecast_window = None
        self.settings_window = None
        self.event_3d_window = None
        self.simulation_window = None
        self.timeline_window = None
        self.table_view = None

        # Keep a reference to the core (business logic) and the currently
        # loaded project
        self.ramsis_core = ramsis.ramsis_core
        self.settings = ramsis.app_settings
        self.project = None

        # Setup the user interface
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.statusBar.setSizeGripEnabled(False)
        # ...additional setup
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer.setVisible(True)
        self.ui.mainToolBar.insertWidget(self.ui.actionForecasts, spacer)

        # Hook up the menu
        # ...File
        self.ui.actionNew_Project.triggered.connect(self.action_new_project)
        self.ui.actionOpen_Project.triggered.connect(self.action_open_project)
        self.ui.actionImport_Seismic_Data.triggered.connect(
            self.action_import_seismic_data)
        self.ui.actionImport_Hydraulic_Data.triggered.connect(
            self.action_import_hydraulic_data)
        self.ui.actionView_Data.triggered.\
            connect(self.action_view_seismic_data)
        self.ui.actionSettings.triggered.connect(self.action_show_settings)
        # ...Simulation
        self.ui.actionStart_Simulation.triggered.\
            connect(self.action_start_simulation)
        self.ui.actionPause_Simulation.triggered.\
            connect(self.action_pause_simulation)
        self.ui.actionStop_Simulation.triggered.\
            connect(self.action_stop_simulation)
        # ...Window
        self.ui.actionForecasts.triggered.connect(self.action_show_forecasts)
        self.ui.actionShow_3D.triggered.connect(self.action_show_3d)
        self.ui.actionTimeline.triggered.connect(self.action_show_timeline)
        self.ui.actionSimulation.triggered.\
            connect(self.action_show_sim_controls)

        # Hook up essential signals from the core and the forecast core
        ramsis.app_launched.connect(self.on_app_launch)
        self.ramsis_core.engine.state_changed.\
            connect(self.on_engine_state_change)
        self.ramsis_core.simulator.state_changed.\
            connect(self.on_sim_state_change)
        self.ramsis_core.project_loaded.connect(self.on_project_load)

    # Qt Signal Slots

    def on_app_launch(self):
        self._refresh_recent_files_menu()
        self.update_status()
        self.update_controls()

    def on_seismic_history_change(self, _):
        self.update_status()

    def on_hydraulic_history_change(self, _):
        self.update_status()

    def on_engine_state_change(self, _):
        self.update_controls()

    def on_sim_state_change(self, _):
        self.update_controls()

    def on_project_load(self, project):
        self.project = project

        # Make sure we get updated on project changes
        project.will_close.connect(self.on_project_will_close)
        project.project_time_changed.connect(self.on_project_time_change)
        project.seismic_history.history_changed.connect(
            self.on_seismic_history_change)
        project.hydraulic_history.history_changed.connect(
            self.on_hydraulic_history_change)
        self.update_status()
        self.update_controls()

    def on_project_will_close(self, project):
        project.will_close.disconnect(self.on_project_will_close)
        project.project_time_changed.disconnect(self.on_project_time_change)
        project.seismic_history.history_changed.disconnect(
            self.on_seismic_history_change)
        project.hydraulic_history.history_changed.disconnect(
            self.on_hydraulic_history_change)
        self.project = None

    def on_project_time_change(self, time):
        self._replot_3d_event_data(time)

    # Menu Actions

    def action_open_project(self):
        home = os.path.expanduser("~")
        path = QtGui.QFileDialog.\
            getOpenFileName(None, 'Open Project', home,
                            'Ramsis Project Files (*.rms)')
        if path == '':
            return
        self._open_project_at_path(path)

    def _open_project_at_path(self, path):
        if path is None:
            return
        if self.ramsis_core.project is not None:
            self.ramsis_core.close_project()
        self.ramsis_core.open_project(str(path))
        # Update the list of recent files
        recent_files = self.settings.value('recent_files')
        if recent_files is None:
            recent_files = []
        if path in recent_files:
            recent_files.insert(0, recent_files.pop(recent_files.index(path)))
        else:
            recent_files.insert(0, path)
        del recent_files[4:]
        self.settings.set_value('recent_files', recent_files)
        self._refresh_recent_files_menu()

    def _refresh_recent_files_menu(self):
        files = self.settings.value('recent_files')
        self.ui.menuOpen_Recent.clear()
        if files is None:
            return
        for path in files:
            path = str(path)
            file_name = os.path.basename(path)
            file_action = QtGui.QAction(file_name, self)
            file_action.setData(path)
            file_action.triggered.connect(self.action_open_recent)
            self.ui.menuOpen_Recent.addAction(file_action)

    def action_open_recent(self):
        sender_action = self.sender()
        path = str(sender_action.data())
        self._open_project_at_path(path)

    def action_new_project(self):
        home = os.path.expanduser("~")
        path = QtGui.QFileDialog.\
            getSaveFileName(None, 'New Project', home,
                            'Ramsis Project Files (*.rms)')
        self.ramsis_core.create_project(path)

    def action_import_seismic_data(self):
        home = os.path.expanduser("~")
        path = QtGui.QFileDialog.getOpenFileName(None,
                                                 'Open seismic data file',
                                                 home)
        if path == '':
            return
        history = self.project.seismic_history
        if path:
            self._import_file_to_history(path, history)

    def action_import_hydraulic_data(self):
        home = os.path.expanduser("~")
        path = QtGui.QFileDialog.getOpenFileName(None,
                                                 'Open hydraulic data file',
                                                 home)
        if path == '':
            return
        history = self.project.hydraulic_history
        if path:
            self._import_file_to_history(path, history, delimiter='\t')

    @staticmethod
    def _import_file_to_history(path, history, delimiter=' '):
        """
        Import happens on the view level (instead of inside Project) because
        the process is interactive. The function checks if the file contains
        relative dates. If yes, the user is asked to provide a base date.

        """
        with open(path, 'rb') as csv_file:
            importer = EventImporter(csv_file, delimiter=delimiter)
            if importer.expects_base_date:
                date, accepted = helpers.DateDialog.get_date_time()
                if not accepted:
                    return
                importer.base_date = date
            else:
                importer.date_format = '%d.%m.%YT%H:%M:%S'
            history.import_events(importer)

    def action_show_forecasts(self):
        if self.forecast_window is None:
            self.forecast_window = \
                ForecastsWindow(ramsis_core=self.ramsis_core, parent=self)
        self.forecast_window.show()

    def action_show_timeline(self):
        if self.timeline_window is None:
            self.timeline_window = TimelineWindow(ramsis_core=self.ramsis_core,
                                                  parent=self)
        self.timeline_window.show()

    def action_show_sim_controls(self):
        if self.simulation_window is None:
            self.simulation_window = \
                SimulationWindow(ramsis_core=self.ramsis_core, parent=self)
        self.simulation_window.show()

    def action_show_3d(self):
        self.event_3d_window = Event3DViewWidget()
        self.event_3d_window.show()

    def action_show_settings(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow(settings=self.settings)
        self.settings_window.show()

    def action_view_seismic_data(self):
        if self.table_view is None:
            self.table_view = QtGui.QTableView()
            model = SeismicDataModel(self.project.seismic_history)
            self.table_view.setModel(model)
            self.table_view.show()

    # ... Simulation

    def action_start_simulation(self):
        # speed = self.ui.speedBox.value()
        # self.ramsis_core.simulator.speed = speed
        self.ramsis_core.start()

    def action_pause_simulation(self):
        self.ramsis_core.pause()

    def action_stop_simulation(self):
        self.ramsis_core.stop()

    # Menu Enabled State Updates

    def update_controls(self):
        if self.project is None:
            enable = False
        else:
            enable = True
        self.ui.actionTimeline.setEnabled(enable)
        self.ui.actionShow_3D.setEnabled(enable)
        self.ui.actionForecasts.setEnabled(enable)
        self.ui.actionSimulation.setEnabled(enable)
        self.ui.actionScenario.setEnabled(enable)
        self.ui.actionView_Data.setEnabled(enable)

        engine_state = self.ramsis_core.engine.state
        if engine_state == EngineState.INACTIVE:
            self.ui.actionStart_Simulation.setEnabled(False)
            self.ui.actionPause_Simulation.setEnabled(False)
            self.ui.actionStop_Simulation.setEnabled(False)
            return
        sim_state = self.ramsis_core.simulator.state
        if sim_state == SimulatorState.RUNNING:
            self.ui.actionStart_Simulation.setEnabled(False)
            self.ui.actionPause_Simulation.setEnabled(True)
            self.ui.actionStop_Simulation.setEnabled(True)
        elif sim_state == SimulatorState.PAUSED:
            self.ui.actionStart_Simulation.setEnabled(True)
            self.ui.actionPause_Simulation.setEnabled(False)
            self.ui.actionStop_Simulation.setEnabled(True)
        else:
            # STOPPED
            self.ui.actionStart_Simulation.setEnabled(True)
            self.ui.actionPause_Simulation.setEnabled(False)
            self.ui.actionStop_Simulation.setEnabled(False)

    # Status Updates

    def update_status(self):
        """
        Updates the status message in the status bar.

        """
        if self.project is None:
            self.ui.projectNameLabel.setText('No project loaded')
            self.ui.startDateLabel.setText('Starts: -')
            self.ui.endDateLabel.setText('Ends: -')
            self.ui.seismicEventCountLabel.setText('0 seismic events')
            self.ui.exposureDataLabel.setText('No exposure data available')
            self.ui.boreholeDataLabel.setText('No borehole data available')
            return
        else:
            self.ui.projectNameLabel.setText(self.project.title)
            time_range = self.project.event_time_range()
            self.ui.startDateLabel.setText(
                'Starts: {}'.format(time_range[0]))
            self.ui.endDateLabel.setText(
                'Ends: {}'.format(time_range[1]))
            self.ui.seismicEventCountLabel.setText(
                '{} seismic events'.format(len(self.project.seismic_history)))
            # TODO: show real data
            self.ui.exposureDataLabel.setText('Exposure data available '
                                              'for 10 locations')
            self.ui.boreholeDataLabel.setText('1 Borehole')

        state_msg = 'RAMSIS is idle'
        if self.ramsis_core.simulator.state == SimulatorState.RUNNING:
            state_msg = 'Simulating'
        elif self.ramsis_core.simulator.state == SimulatorState.PAUSED:
            state_msg = 'Simulating (paused)'

        self.statusBar().showMessage(state_msg)

    # Plot Helpers

    def _replot_3d_event_data(self, t):
        events = self.project.seismic_history.events_before(t)
        if self.event_3d_window is None or len(events) == 0:
            return
        loc = np.array([(e.x, e.y, e.z) for e in events])
        well = self.project.injection_well
        center = np.array((well.well_tip_x, well.well_tip_y, well.well_tip_z))
        loc -= center
        size = np.array([e.magnitude for e in events])
        self.event_3d_window.show_events(loc, size)
