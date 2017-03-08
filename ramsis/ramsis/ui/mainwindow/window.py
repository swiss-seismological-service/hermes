# -*- encoding: utf-8 -*-
"""
Controller class for the main window

Takes care of setting up the main GUI, handling any menu actions and updating
top level controls as necessary.
We delegate the presentation of content to a content presenter so that this
class does not become too big.

Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED

"""

import logging
import os
from PyQt4 import QtGui, uic
from PyQt4.QtGui import QSizePolicy, QWidget, QStatusBar, QLabel
import ui.ramsisuihelpers as helpers
from ui.settingswindow import ApplicationSettingsWindow, ProjectSettingsWindow
from ui.simulationwindow import SimulationWindow
from ui.timelinewindow import TimelineWindow
from ui.views.plots import Event3DViewWidget
from presenter import ContentPresenter
from viewmodels.seismicdatamodel import SeismicDataModel
from core.simulator import SimulatorState
from core.tools.eventimporter import EventImporter


ui_path = os.path.dirname(__file__)
MAIN_WINDOW_PATH = os.path.join('ramsis', 'ui', 'views', 'mainwindow.ui')
Ui_MainWindow = uic.loadUiType(MAIN_WINDOW_PATH)[0]


class StatusBar(QStatusBar):

    def __init__(self):
        super(StatusBar, self).__init__()
        self.projectWidget = QLabel('No project loaded')
        self.timeWidget = QLabel('Project Time: N/A')
        self.addWidget(self.projectWidget)
        self.addWidget(QLabel(' '*10))
        self.addWidget(self.timeWidget)

    def set_project(self, project):
        txt = project.title if project else 'No project loaded'
        self.projectWidget.setText(txt)
        self.set_project_time(project.project_time if project else None)

    def set_project_time(self, t):
        txt = t.strftime('%d.%m.%Y %H:%M:%S') if t else 'N/A'
        self.timeWidget.setText('Project Time: {}'.format(txt))


class MainWindow(QtGui.QMainWindow):

    def __init__(self, ramsis, **kwargs):
        QtGui.QDialog.__init__(self, **kwargs)
        self.logger = logging.getLogger(__name__)

        # Other windows which we lazy-load
        self.application_settings_window = None
        self.project_settings_window = None
        self.event_3d_window = None
        self.simulation_window = None
        self.timeline_window = None
        self.table_view = None

        # References
        self.ramsis_core = ramsis.ramsis_core
        self.application_settings = ramsis.app_settings

        # Setup the user interface
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # ...additional setup
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer.setVisible(True)
        self.ui.mainToolBar.insertWidget(self.ui.actionForecasts, spacer)
        self.status_bar = StatusBar()
        self.setStatusBar(self.status_bar)

        # Delegate content presentation
        self.content_presenter = ContentPresenter(self.ramsis_core, self.ui)

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
        self.ui.actionApplication_Settings.triggered.connect(
            self.action_show_application_settings)
        self.ui.actionProject_Settings.triggered.connect(
            self.action_show_project_settings)
        # ...Simulation
        self.ui.actionStart_Simulation.triggered.\
            connect(self.action_start_simulation)
        self.ui.actionPause_Simulation.triggered.\
            connect(self.action_pause_simulation)
        self.ui.actionStop_Simulation.triggered.\
            connect(self.action_stop_simulation)
        # ...Window
        self.ui.actionShow_3D.triggered.connect(self.action_show_3d)
        self.ui.actionTimeline.triggered.connect(self.action_show_timeline)
        self.ui.actionSimulation.triggered.\
            connect(self.action_show_sim_controls)

        # Connect essential signals
        # ... from the core
        ramsis.app_launched.connect(self.on_app_launch)
        self.ramsis_core.project_loaded.connect(self.on_project_load)
        self.ramsis_core.simulator.state_changed.\
            connect(self.on_sim_state_change)

    # Menu Actions

    def action_open_project(self):
        home = os.path.expanduser("~")
        path = QtGui.QFileDialog. \
            getOpenFileName(None, 'Open Project', home,
                            'Ramsis Project Files (*.db)')
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
        recent_files = self.application_settings.value('recent_files')
        if recent_files is None:
            recent_files = []
        if path in recent_files:
            recent_files.insert(0,
                                recent_files.pop(recent_files.index(path)))
        else:
            recent_files.insert(0, path)
        del recent_files[4:]
        self.application_settings.set_value('recent_files', recent_files)
        self._refresh_recent_files_menu()

    def _refresh_recent_files_menu(self):
        files = self.application_settings.value('recent_files')
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
        path = QtGui.QFileDialog. \
            getSaveFileName(None, 'New Project', home,
                            'Ramsis Project Files (*.db)')
        if not path.endswith('.db'):
            path += '.db'
        self.ramsis_core.create_project(path)
        self._open_project_at_path(path)

    def action_import_seismic_data(self):
        home = os.path.expanduser("~")
        path = QtGui.QFileDialog.getOpenFileName(None,
                                                 'Open seismic data file',
                                                 home)
        if path == '':
            return
        history = self.ramsis_core.project.seismic_catalog
        if path:
            self._import_file_to_history(path, history)

    def action_import_hydraulic_data(self):
        home = os.path.expanduser("~")
        path = QtGui.QFileDialog.getOpenFileName(None,
                                                 'Open hydraulic data file',
                                                 home)
        if path == '':
            return
        history = self.ramsis_core.project.injection_history
        if path:
            self._import_file_to_history(path, history, delimiter='\t')

    def _import_file_to_history(self, path, history, delimiter=' '):
        """
        Import happens on the view level (instead of inside Project) because
        the process is interactive. The function checks if the file contains
        relative dates. If yes, the user is asked to provide a base date.

        :param str path: Path to csv file
        :param SeismicCatalog | HydraulicHistory: Target history
        :param str delimiter: Delimiter used to delimit records

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
            history.clear()
            history.import_events(importer)
            self.ramsis_core.project.save()

    def action_show_timeline(self):
        if self.timeline_window is None:
            self.timeline_window = TimelineWindow(
                ramsis_core=self.ramsis_core,
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

    def action_show_application_settings(self):
        if self.application_settings_window is None:
            self.application_settings_window = \
                ApplicationSettingsWindow(
                    settings=self.application_settings)
        self.application_settings_window.show()

    def action_show_project_settings(self):
        if self.project_settings_window is None:
            self.project_settings_window = \
                ProjectSettingsWindow(project=self.ramsis_core.project)
        self.project_settings_window.show()

    def action_view_seismic_data(self):
        if self.table_view is None:
            self.table_view = QtGui.QTableView()
            model = SeismicDataModel(self.ramsis_core.project.seismic_catalog)
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
        if self.ramsis_core.project is None:
            enable = False
        else:
            enable = True
        self.ui.menuProject.setEnabled(enable)
        self.ui.actionTimeline.setEnabled(enable)
        self.ui.actionShow_3D.setEnabled(enable)
        self.ui.actionForecasts.setEnabled(enable)
        self.ui.actionSimulation.setEnabled(enable)
        self.ui.actionScenario.setEnabled(enable)

        if not self.ramsis_core.project:
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

    def update_status_msg(self):
        """
        Updates the status message in the status bar.

        """
        state_msg = 'RAMSIS is idle'
        if self.ramsis_core.simulator.state == SimulatorState.RUNNING:
            state_msg = 'Simulating'
        elif self.ramsis_core.simulator.state == SimulatorState.PAUSED:
            state_msg = 'Simulating (paused)'

        self.status_bar.showMessage(state_msg)

    # Handlers for signals from the core

    def on_app_launch(self):
        self._refresh_recent_files_menu()
        self.update_controls()

    def on_project_will_close(self, _):
        self.status_bar.set_project(None)
        self.update_controls()

    def on_project_time_change(self, t):
        self.status_bar.set_project_time(t)
        self.update_status_msg()

    def on_project_load(self, project):
        """
        :param project: RAMSIS project
        :type project: Project

        """
        self.content_presenter.present_current_project()
        self.status_bar.set_project(project)
        self.update_controls()

    def on_sim_state_change(self, _):
        self.update_controls()
        self.update_status_msg()
