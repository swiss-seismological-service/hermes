# -*- encoding: utf-8 -*-
"""
Controller class for the main window

Takes care of setting up the main GUI, handling any menu actions and updating
top level controls as necessary.
We delegate the presentation of content to a content presenter so that this
class does not become too big.

Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED

"""

import datetime
import logging
import os

from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, QDateTime
from PyQt5.QtWidgets import QSizePolicy, QWidget, QStatusBar, QLabel, \
    QMessageBox, QProgressBar, QMainWindow, QAction, QFileDialog, QTableView, \
    QDateTimeEdit, QDialogButtonBox, QDialog, QVBoxLayout

from RAMSIS.core.builder import default_scenario, empty_forecast
from RAMSIS.core.simulator import SimulatorState
from RAMSIS.core.store import EditingContext
from RAMSIS.core.datasources import CsvEventImporter
from RAMSIS.ui.projectmanagementwindow import ProjectManagementWindow
from RAMSIS.ui.settingswindow import (
    ApplicationSettingsWindow, ProjectSettingsWindow)
from RAMSIS.ui.simulationwindow import SimulationWindow
from RAMSIS.ui.reservoirwindow import ReservoirWindow
from RAMSIS.ui.base.utils import utc_to_local
from RAMSIS.ui.base.roles import CustomRoles
from RAMSIS.ui.dialog import ForecastConfigDialog, ScenarioConfigDialog
from RAMSIS.wkt_utils import point_to_proj4

from .presenter import ContentPresenter
from .viewmodels.seismicdatamodel import SeismicDataModel


ui_path = os.path.dirname(__file__)
MAIN_WINDOW_PATH = os.path.join(ui_path, '..', 'views', 'mainwindow.ui')
Ui_MainWindow = uic.loadUiType(
    MAIN_WINDOW_PATH,
    import_from='RAMSIS.ui.views', from_imports=True)[0]


class StatusBar(QStatusBar):

    def __init__(self):
        super(StatusBar, self).__init__()
        self.statusWidget = QLabel('No DB connection')
        self.timeWidget = QLabel('Time: N/A')
        self.progressBar = QProgressBar()
        self.progressBar.setMaximumHeight(15)
        self.progressBar.setMaximumWidth(150)
        self.activityWidget = QLabel('Idle')
        self.current_activity_id = None
        self.addWidget(self.statusWidget)
        self.addWidget(QLabel(' ' * 10))
        self.addWidget(self.timeWidget)
        self.addPermanentWidget(self.activityWidget)
        self.addPermanentWidget(self.progressBar)
        self.progressBar.setHidden(True)
        self.setStyleSheet("QLabel {margin-left: 10px;}")

    def set_status(self, status):
        """
        Displays global application status.

        The global application status is a permanent status message that is
        displayed on the far left of the status bar. If a project is loaded,
        this corresponods to the project name of the currently active project.

        :param str status: Status message

        """
        self.statusWidget.setText(status)

    def set_project(self, project):
        txt = project.title if project else 'No project loaded'
        self.statusWidget.setText(txt)

    def set_time(self, t):
        txt = utc_to_local(t).strftime('%d.%m.%Y %H:%M:%S') if t else 'N/A'
        self.timeWidget.setText('Time: {}'.format(txt))

    def show_activity(self, message, id='default'):
        self.current_activity_id = id
        self.progressBar.setRange(0, 0)
        self.progressBar.setHidden(False)
        self.activityWidget.setText(message)

    def dismiss_activity(self, id='default'):
        if self.current_activity_id == id:
            self.progressBar.setHidden(True)
            self.activityWidget.setText('Idle')
            self.current_activity_id = None


class MainWindow(QMainWindow):

    def __init__(self, app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

        # Other windows which we lazy-load and own
        # TODO: let the toplevel gui object handle these
        self.reservoir_window = None
        self.simulation_window = None
        self.timeline_window = None
        self.table_view = None

        # References
        # TODO: store only ramsis reference and use same name everywhere
        #   (app, core, ..)
        self.app = app
        self.application_settings = app.app_settings

        # Setup the user interface
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # ...additional setup
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer.setVisible(True)
        self.ui.mainToolBar.insertWidget(self.ui.actionShow_3D, spacer)
        self.status_bar = StatusBar()
        self.setStatusBar(self.status_bar)

        # Delegate content presentation
        self.content_presenter = ContentPresenter(self.app.ramsis_core,
                                                  self.ui)

        # Connect essential signals from the core
        app.app_launched.connect(self.on_app_launch)
        app.ramsis_core.store_changed.connect(self.on_store_changed)
        app.ramsis_core.project_loaded.connect(self.on_project_loaded)
        app.ramsis_core.project_will_unload.connect(
            self.on_project_will_unload)
        app.ramsis_core.simulator.state_changed.\
            connect(self.on_sim_state_change)
        app.ramsis_core.clock.time_changed.connect(self.on_time_changed)

    # UI signals

    @pyqtSlot(name='on_addScenarioButton_clicked')
    def on_add_scenario_clicked(self):
        selection_model = self.ui.forecastTreeView.selectionModel()
        idx = selection_model.currentIndex()

        if not idx.isValid():
            _ = QMessageBox.critical(
                self, 'RAMSIS', 'No forecast/scenario item selected.',
                buttons=QMessageBox.Close)
            return

        # check if child was selected
        if idx.parent().isValid():
            idx = idx.parent()

        fc = idx.data(CustomRoles.RepresentedItemRole)

        dlg = ScenarioConfigDialog(
            default_scenario(self.app.ramsis_core.store),
            fc_duration=(fc.endtime - fc.starttime).total_seconds(),
            srs=point_to_proj4(
                self.app.ramsis_core.project.referencepoint) or None)
        dlg.exec_()

        scenario = dlg.data
        if scenario is not None:
            self.logger.debug(f"Dialog data: {dlg.data!r}")

            fc.append(scenario)

            self.app.ramsis_core.store.save()

            self.logger.info(
                f'Created new scenario {scenario!r} for forecast {fc!r}.')
            self.content_presenter.fc_tree_model.add_scenario(idx, scenario)

    @pyqtSlot(name='on_removeScenarioButton_clicked')
    def on_remove_scenario_clicked(self):
        fc_selection = self.ui.forecastTreeView.selectionModel()
        idx = fc_selection.currentIndex()
        if not idx.parent().isValid():
            return
        scenario = idx.data(role=CustomRoles.RepresentedItemRole)
        scenario.forecast.scenarios.remove(scenario)
        self.app.ramsis_core.store.save()

    @pyqtSlot(name='on_planNextButton_clicked')
    def on_plan_next_forecast_clicked(self):
        dt = datetime.datetime(2000, 1, 1)
        dlg = ForecastConfigDialog(
            empty_forecast(starttime=dt, endtime=dt),
            min_datetime=self.app.ramsis_core.project.starttime)
        dlg.exec_()

        if dlg.result() == QDialog.Accepted:
            fc = dlg.data
            self.app.ramsis_core.add_forecast(fc)
            self.content_presenter.add_forecast(fc)

    @pyqtSlot(name='on_actionApplication_Settings_triggered')
    def show_application_settings(self):
        window = ApplicationSettingsWindow(self.app)
        window.show()
        self.app.gui.manage_window(window)

    @pyqtSlot(name='on_actionProject_Settings_triggered')
    def show_project_settings(self):
        editing_context = EditingContext(self.app.ramsis_core.store)
        editable_project = editing_context.get(self.app.ramsis_core.project)

        def on_save(project):
            editing_context.save()

        window = ProjectSettingsWindow(project=editable_project)
        window.save_callback = on_save
        window.show()
        self.app.gui.manage_window(window)

    @pyqtSlot(name='on_actionManage_Projects_triggered')
    def manage_projects(self):
        window = ProjectManagementWindow(self.app)
        window.show()
        self.app.gui.manage_window(window)

    @pyqtSlot(name='on_actionFetch_from_fdsnws_triggered')
    def action_fetch_seismic_data(self):
        self.status_bar.show_activity('Fetching seismic data...',
                                      id='fdsn_fetch')
        self.app.ramsis_core.fetch_seismic_events()

    @pyqtSlot(name='on_actionImport_Seismic_Data_triggered')
    def action_import_seismic_data(self):
        """ Import seismic data manually """
        home = os.path.expanduser("~")
        path = QFileDialog.getOpenFileName(None,
                                           'Open seismic data file',
                                           home)
        if not path or path[0] == '':
            return
        with open(path[0]) as ifd:
            importer = _create_csv_importer_interactive(file)
            self.app.ramsis_core.import_seismic_events(importer)

    @pyqtSlot(name='on_actionFetch_from_hydws_triggered')
    def action_fetch_hydraulic_data(self):
        self.status_bar.show_activity('Fetching hydraulic data...',
                                      id='hydws_fetch')
        self.app.ramsis_core.fetch_hydraulic_events()

    @pyqtSlot(name='on_actionImport_Hydraulic_Data_triggered')
    def action_import_hydraulic_data(self):
        """ Import hydraulic data manually """
        # TODO LH: re-implement using io.
        home = os.path.expanduser("~")
        path = QFileDialog.getOpenFileName(None,
                                           'Open hydraulic data file',
                                           home)
        if not path or path[0] == '':
            return
        with open(path[0]) as file:
            importer = _create_csv_importer_interactive(file, delimiter='\t')
            self.app.ramsis_core.import_hydraulic_events(importer)

    @pyqtSlot(name='on_actionDelete_Results_triggered')
    def action_delete_results(self):
        reply = QMessageBox.question(
            self,
            "Delete results",
            "Are you sure you want to delete all forecast results? This "
            "cannot be undone!",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.app.ramsis_core.reset_forecasts()

    @pyqtSlot(name='on_actionSimulation_triggered')
    def action_show_sim_controls(self):
        if self.simulation_window is None:
            self.simulation_window = \
                SimulationWindow(ramsis_core=self.app.ramsis_core, parent=self)
        self.simulation_window.show()

    @pyqtSlot(name='on_actionShow_3D_triggered')
    def action_show_3d(self):
        self.reservoir_window = ReservoirWindow(self.app.ramsis_core)
        self.reservoir_window.show()
        self.reservoir_window.draw_catalog()

    @pyqtSlot(name='on_actionView_Data_triggered')
    def action_view_seismic_data(self):
        if self.table_view is None:
            self.table_view = QTableView()
            model = SeismicDataModel(self.app.ramsis_core.project.
                                     seismiccatalog)
            self.table_view.setModel(model)
            self.table_view.show()

    # ... Simulation

    @pyqtSlot(name='on_actionStart_Simulation_triggered')
    def action_start_simulation(self):
        # speed = self.ui.speedBox.value()
        # self.ramsis_core.simulator.speed = speed
        self.app.ramsis_core.start()

    @pyqtSlot(name='on_actionPause_Simulation_triggered')
    def action_pause_simulation(self):
        self.app.ramsis_core.pause()

    @pyqtSlot(name='on_actionStop_Simulation_triggered')
    def action_stop_simulation(self):
        self.app.ramsis_core.stop()

    # Menu Enabled State Updates

    def update_controls(self):
        # TODO LH: Use a UiStateMachine to manage control states
        enable_with_project = [
            'menuProject',
            'actionShow_3D', 'actionSimulation',
            'actionScenario', 'planNextButton', 'addScenarioButton',
            'removeScenarioButton',
        ]
        enable = True if self.app.ramsis_core.project is not None else False
        for ui_element in enable_with_project:
            getattr(self.ui, ui_element).setEnabled(enable)

        project = self.app.ramsis_core.project
        if not project:
            self.ui.actionProject_Settings.setEnabled(False)
            self.ui.actionStart_Simulation.setEnabled(False)
            self.ui.actionPause_Simulation.setEnabled(False)
            self.ui.actionStop_Simulation.setEnabled(False)
            return
        self.ui.actionProject_Settings.setEnabled(True)
        sim_state = self.app.ramsis_core.simulator.state
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

        en = (project.settings['fdsnws_enable'] is True and
              project.settings['fdsnws_url'] is not None)
        self.ui.actionFetch_from_fdsnws.setEnabled(en)

        en = (project.settings['hydws_enable'] is True and
              project.settings['hydws_url'] is not None)
        self.ui.actionFetch_from_hydws.setEnabled(en)

    # Status Updates

    def update_status_msg(self):
        """
        Updates the status message in the status bar.

        """
        if self.app.ramsis_core.simulator.state == SimulatorState.RUNNING:
            state_msg = 'Simulating'
        elif self.app.ramsis_core.simulator.state == SimulatorState.PAUSED:
            state_msg = 'Simulating (paused)'
        else:
            self.status_bar.dismiss_activity('simulator_state')
            return

        self.status_bar.show_activity(state_msg, 'simulator_state')

    # Handlers for signals from the core

    def on_app_launch(self):
        self.update_controls()

    def on_store_changed(self):
        if self.sender().store:
            self.status_bar.set_status('No project loaded')
        else:
            self.status_bar.set_status('No DB connection')

    def on_time_changed(self, t):
        self.status_bar.set_time(t)

    def on_project_loaded(self, project):
        """
        :param project: RAMSIS project
        :type project: Project

        """
        self.content_presenter.show_project()
        self.status_bar.set_status(project.name)
        self.status_bar.set_time(self.app.ramsis_core.clock.time)
        #project.settings.settings_changed.connect(
        #    self.on_project_settings_changed)
        #project.seismiccatalog.history_changed.connect(
        #    self.on_catalog_changed)
        self.update_controls()

    def on_project_will_unload(self, _):
        self.status_bar.set_status('No project loaded')
        self.content_presenter.clear_project()
        self.update_controls()

    def on_catalog_changed(self, _):
        self.status_bar.dismiss_activity('fdsn_fetch')

    def on_sim_state_change(self, _):
        self.update_controls()
        self.update_status_msg()

    def on_project_settings_changed(self, settings):
        self.update_controls()
        self.status_bar.set_status(self.app.ramsis_core.project.name)
        # TODO LH: update presenters since project settings are not observable
        #   anymore


class DateDialog(QDialog):
    def __init__(self, parent=None):
        super(DateDialog, self).__init__(parent)

        layout = QVBoxLayout(self)

        # info text
        self.label = QLabel(
            text='The file appears to contain relative dates.\n'
                 'Please specify a reference date.')
        layout.addWidget(self.label)

        # nice widget for editing the date
        self.datetime = QDateTimeEdit(self)
        self.datetime.setCalendarPopup(True)
        self.datetime.setDisplayFormat('yyyy-MM-dd hh:mm:ss')
        self.datetime.setDateTime(QDateTime.currentDateTime())
        layout.addWidget(self.datetime)

        # OK and Cancel buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok |
                                        QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout.addWidget(self.buttons)
        self.setLayout(layout)

    # get current date and time from the dialog
    def date_time(self):
        return self.datetime.dateTime()

    # static method to create the dialog and return (date, time, accepted)
    @staticmethod
    def get_date_time(parent=None):
        dialog = DateDialog(parent)
        result = dialog.exec_()
        date = dialog.date_time()
        return date.toPyDateTime(), result == QDialog.Accepted


def _create_csv_importer_interactive(file, delimiter=','):
    importer = CsvEventImporter(file, delimiter=delimiter)
    if importer.expects_base_date:
        date, accepted = DateDialog.get_date_time()
        if not accepted:
            return
        importer.base_date = date
    else:
        importer.date_format = '%Y-%m-%dT%H:%M:%S'
    return importer
