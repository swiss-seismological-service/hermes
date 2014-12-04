# -*- encoding: utf-8 -*-
"""
Controller module for the main window

"""

from datetime import datetime
import os
import logging

from PyQt4 import QtGui

from views.ui_mainwindow import Ui_MainWindow
from forecastswindow import ForecastsWindow
from settingswindow import SettingsWindow
from eventimporter import EventImporter
import atlsuihelpers as helpers
from viewmodels.seismicdatamodel import SeismicDataModel
from core.engine import EngineState
from simulator import SimulatorState
from ui.views.plots import DisplayRange, Event3DViewWidget
import numpy as np



# Create a class for our main window
class MainWindow(QtGui.QMainWindow):
    """
    Class that manages the main application window

    """

    def __init__(self, atls):
        QtGui.QMainWindow.__init__(self)
        self.logger = logging.getLogger(__name__)

        # Other windows which are lazy-loaded
        self.forecast_window = None
        self.settings_window = None
        self.event_3d_window = None

        # Project time as displayed in status bar
        self.displayed_project_time = datetime.now()

        # Keep a reference to the core (business logic) and the currently
        # loaded project
        self.atls_core = atls.atls_core
        self.settings = atls.app_settings
        self.project = None

        # Setup the user interface
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Hook up the menu
        # ...File
        self.ui.actionNew_Project.triggered.connect(self.action_new_project)
        self.ui.actionOpen_Project.triggered.connect(self.action_open_project)
        self.ui.actionImport_Seismic_Data.triggered.connect(
            self.action_import_seismic_data)
        self.ui.actionImport_Hydraulic_Data.triggered.connect(
            self.action_import_hydraulic_data)
        self.ui.actionView_Data.triggered.connect(self.action_view_seismic_data)
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

        # Hook up buttons
        self.ui.startButton.clicked.connect(self.action_start_simulation)
        self.ui.stopButton.clicked.connect(self.action_stop_simulation)
        self.ui.pauseButton.clicked.connect(self.action_pause_simulation)

        # Hook up essential signals from the core and the forecast core
        atls.app_launched.connect(self.on_app_launch)
        self.atls_core.engine.state_changed.connect(self.on_engine_state_change)
        self.atls_core.simulator.state_changed.connect(self.on_sim_state_change)
        self.atls_core.project_loaded.connect(self.on_project_load)

        # Link the x axis of the seismicity view with the x axis of the
        # hydraulics view
        h_view = self.ui.hydraulic_data_plot.plotItem.getViewBox()
        s_view = self.ui.seismic_data_plot.plotItem.getViewBox()
        h_view.setXLink(s_view)

    # Qt Signal Slots

    def on_app_launch(self):
        self._refresh_recent_files_menu()
        self.update_status()
        self.update_controls()

    def on_seismic_history_change(self, dict):
        time = dict.get('simulation_time')
        if time is None:
            self._replot_seismic_data()
        else:
            self._replot_seismic_data(update=True, max_time=time)
        self.update_status()

    def on_hydraulic_history_change(self, dict):
        time = dict.get('simulation_time')
        if time is None:
            self._replot_hydraulic_data()
        else:
            self._replot_hydraulic_data(update=True, max_time=time)
        self.update_status()

    def on_engine_state_change(self, state):
        self.update_controls()
        self.update_status()

    def on_sim_state_change(self, state):
        self.update_controls()
        self.update_status()

    def on_project_load(self, project):
        self.project = project

        # Make sure we get updated on project changes
        project.will_close.connect(self.on_project_will_close)
        project.project_time_changed.connect(self.on_project_time_change)
        project.seismic_history.history_changed.connect(
            self.on_seismic_history_change)
        project.hydraulic_history.history_changed.connect(
            self.on_hydraulic_history_change)

        # Update all plots and our status
        self._replot_hydraulic_data()
        self._replot_seismic_data()
        self.ui.seismic_data_plot.zoom(display_range=DisplayRange.WEEK)
        # Trigger a project time change manually, so the plots will update
        self.on_project_time_change(project.project_time)

    def on_project_will_close(self, project):
        self.project = None
        self._clear_plots()

    def on_project_time_change(self, time):
        dt = (time - self.displayed_project_time).total_seconds()
        self.displayed_project_time = time
        # we do a more efficient relative change if the change is not too big
        if abs(dt) > self.ui.seismic_data_plot.display_range:
            epoch = datetime(1970, 1, 1)
            pos = (time - epoch).total_seconds()
            self.ui.seismic_data_plot.marker_pos = pos
            self.ui.hydraulic_data_plot.marker_pos = pos
            self.ui.seismic_data_plot.zoom_to_marker()
        else:
            self.ui.seismic_data_plot.advance_time(dt)
            self.ui.hydraulic_data_plot.advance_time(dt)
        self.update_status()
        self._replot_3d_event_data(time)

    # Menu Actions

    def action_open_project(self):
        home = os.path.expanduser("~")
        path = QtGui.QFileDialog.getOpenFileName(None,
                                                 'Open Project',
                                                 home,
                                                 'Atls Project Files (*.atl)')
        self._open_project_at_path(path)

    def _open_project_at_path(self, path):
        if path is None:
            return
        if self.atls_core.project is not None:
            self.atls_core.close_project()
        self.atls_core.open_project(str(path))
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

    def action_open_recent(self, path):
        sender_action = self.sender()
        path = str(sender_action.data())
        self._open_project_at_path(path)

    def action_new_project(self):
        home = os.path.expanduser("~")
        path = QtGui.QFileDialog.getSaveFileName(None,
                                                 'New Project',
                                                 home,
                                                 'Atls Project Files (*.atl)')
        self.atls_core.create_project(path)

    def action_import_seismic_data(self):
        home = os.path.expanduser("~")
        path = QtGui.QFileDialog.getOpenFileName(None,
                                                 'Open seismic data file',
                                                 home)
        history = self.project.seismic_history
        if path:
            self._import_file_to_history(path, history)

    def action_import_hydraulic_data(self):
        home = os.path.expanduser("~")
        path = QtGui.QFileDialog.getOpenFileName(None,
                                                 'Open hydraulic data file',
                                                 home)
        history = self.project.hydraulic_history
        if path:
            self._import_file_to_history(path, history, delimiter='\t')

    def _import_file_to_history(self, path, history, delimiter=' '):
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
            self.forecast_window = ForecastsWindow(atls_core=self.atls_core,
                                                   parent=self)
        self.forecast_window.show()

    def action_show_3d(self):
        self.event_3d_window = Event3DViewWidget()
        self.event_3d_window.show()

    def action_show_settings(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow(settings=self.settings)
        self.settings_window.show()

    def action_view_seismic_data(self):
        self.table_view = QtGui.QTableView()
        model = SeismicDataModel(self.project.seismic_history)
        self.table_view.setModel(model)
        self.table_view.show()

    # ... Simulation

    def action_start_simulation(self):
        #speed = self.ui.speedBox.value()
        #self.atls_core.simulator.speed = speed
        self.atls_core.start()

    def action_pause_simulation(self):
        self.atls_core.pause()

    def action_stop_simulation(self):
        self.atls_core.stop()

    # Control Updates

    def update_controls(self):
        engine_state = self.atls_core.engine.state
        if engine_state == EngineState.INACTIVE:
            self.ui.actionStart_Simulation.setEnabled(False)
            self.ui.actionPause_Simulation.setEnabled(False)
            self.ui.actionStop_Simulation.setEnabled(False)
            self.ui.startButton.setEnabled(False)
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(False)
            return
        sim_state = self.atls_core.simulator.state
        if sim_state == SimulatorState.RUNNING:
            self.ui.actionStart_Simulation.setEnabled(False)
            self.ui.actionPause_Simulation.setEnabled(True)
            self.ui.actionStop_Simulation.setEnabled(True)
            self.ui.startButton.setEnabled(False)
            self.ui.pauseButton.setEnabled(True)
            self.ui.stopButton.setEnabled(True)
        elif sim_state == SimulatorState.PAUSED:
            self.ui.actionStart_Simulation.setEnabled(True)
            self.ui.actionPause_Simulation.setEnabled(False)
            self.ui.actionStop_Simulation.setEnabled(True)
            self.ui.startButton.setEnabled(True)
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(True)
        else:
            # STOPPED
            self.ui.actionStart_Simulation.setEnabled(True)
            self.ui.actionPause_Simulation.setEnabled(False)
            self.ui.actionStop_Simulation.setEnabled(False)
            self.ui.startButton.setEnabled(True)
            self.ui.pauseButton.setEnabled(False)
            self.ui.stopButton.setEnabled(False)

    # Status Updates

    def update_status(self):
        """
        Updates the status message in the status bar.

        """
        if self.project is None:
            self.ui.coreStatusLabel.setText('Idle')
            self.ui.projectTimeLabel.setText('-')
            self.ui.lastEventLabel.setText('-')
            self.statusBar().showMessage('No project loaded')
            self.ui.nextForecastLabel.setText('-')
            return

        core = self.atls_core
        time = self.project.project_time
        t_forecast = core.engine.t_next_forecast
        speed = self.atls_core.simulator.speed
        if core.simulator.state == SimulatorState.RUNNING:
            event = self.project.seismic_history.latest_event(time)
            status = 'Simulating at ' + str(speed) + 'x'
            if core.engine.state == EngineState.BUSY:
                status += ' - Computing Forecast'
            self.ui.coreStatusLabel.setText(status)
            self.ui.projectTimeLabel.\
                setText(self.displayed_project_time.ctime())
            self.ui.lastEventLabel.setText(str(event))
            self.ui.nextForecastLabel.setText(str(t_forecast.ctime()))
        elif core.simulator.state == SimulatorState.PAUSED:
            event = self.project.seismic_history.latest_event(time)
            self.ui.coreStatusLabel.setText('Paused')
            self.ui.projectTimeLabel.setText(str(self.displayed_project_time))
            self.ui.lastEventLabel.setText(str(event))
            self.ui.nextForecastLabel.setText(str(t_forecast.ctime()))
        else:
            num_events = len(self.project.seismic_history)
            self.ui.coreStatusLabel.setText('Idle')
            self.ui.projectTimeLabel.setText(str(self.displayed_project_time))
            self.ui.lastEventLabel.setText('-')
            self.statusBar().showMessage(str(num_events) +
                                         ' events in seismic catalog')
            self.ui.nextForecastLabel.setText('-')

    # Plot Helpers

    def _clear_plots(self):
        self.ui.seismic_data_plot.plot.setData()
        self.ui.hydraulic_data_plot.plot.setData()

    def _replot_seismic_data(self, update=False, max_time=None):
        """
        Plot the data in the seismic catalog

        :param max_time: if not None, plot catalog up to max_time only
        :param update: If false (default) the entire catalog is replotted
        :type update: bool

        """
        epoch = datetime(1970, 1, 1)
        events = self.project.seismic_history.all_events()
        if max_time:
            data = [((e.date_time - epoch).total_seconds(), e.magnitude)
                    for e in events if e.date_time < max_time]
        else:
            data = [((e.date_time - epoch).total_seconds(), e.magnitude)
                    for e in events]
        self.ui.seismic_data_plot.plot.setData(pos=data)

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

    def _replot_hydraulic_data(self, update=False, max_time=None):
        """
        Plot the data in the hydraulic catalog

        :param max_time: if not None, plot catalog up to max_time only
        :param update: If false (default) the entire catalog is replotted
        :type update: bool

        """
        epoch = datetime(1970, 1, 1)
        events = self.project.hydraulic_history.all_events()
        if max_time is None:
            max_time = datetime.max

        data = [((e.date_time - epoch).total_seconds(), e.flow_xt)
                for e in events if e.date_time < max_time]

        x, y = map(list, zip(*data)) if len(data) > 0 else ([], [])
        self.ui.hydraulic_data_plot.plot.setData(x, y)