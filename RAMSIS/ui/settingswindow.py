# -*- encoding: utf-8 -*-
"""
Controller class for the settings window

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import logging
import os

from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QDialog, QMessageBox

from RAMSIS.core.controller import LaunchMode
from RAMSIS.ui.utils import UiForm
from RAMSIS.ui.base.state import UiStateMachine

from .modelconfigurationwindow import ModelConfigurationWindow
from RAMSIS.ui.base.controlinterface import control_interface
from RAMSIS.ui.base.utils import utc_to_local, pyqt_local_to_utc_ua

ui_path = os.path.dirname(__file__)
PROJECT_SETTINGS_WINDOW_PATH = \
    os.path.join(ui_path, 'views', 'projectsettingswindow.ui')
Ui_ProjectSettingsWindow = \
    uic.loadUiType(
        PROJECT_SETTINGS_WINDOW_PATH,
        import_from='RAMSIS.ui.views', from_imports=True)[0]


class SettingsWindow(QDialog):

    def __init__(self):
        super(SettingsWindow, self).__init__()
        self.widget_map = {}
        self.key_map = {}

    def register_widgets(self, widget_map):
        self.widget_map = widget_map
        # Invert the mapping for reverse lookups when values change
        self.key_map = dict((v, k) for k, v in self.widget_map.items())

    def action_cancel(self):
        self.close()

    def action_setting_changed(self):
        pass

    def start_observing_changes(self):
        """ Observe changes on all settings widgets """
        for widget in self.widget_map.values():
            signal = control_interface(widget).change_signal()
            signal.connect(self.action_setting_changed)


class DbUiStateMachine(UiStateMachine):
    """ State machine for DB related UI elements in app settings window """

    def __init__(self, ui, *args, **kwargs):
        """
        Initializer

        :param ui: Reference to the ui form class
        :param args: Positional arguments passed on to `UiStateMachine`
        :param kwargs: Keyword arguments passed on to `UiStateMachine`
        """
        super().__init__(*args, **kwargs)
        self.ui = ui
        edit_widgets = [ui.dbUrlEdit, ui.dbNameEdit, ui.dbUserEdit,
                        ui.dbPasswordEdit]
        self.add_states([
            {'name': 'disconnected',
             'ui_disable': ui.dbInitButton,
             'ui_enable': edit_widgets,
             'ui_text': {ui.dbConnectButton: 'Connect',
                         ui.dbStatusLabel: 'Disconnected'},
             'children': [{'name': 'invalid',
                           'ui_disable': ui.dbConnectButton},
                          {'name': 'valid',
                           'ui_enable': ui.dbConnectButton}]},
            {'name': 'connected',
             'ui_disable': edit_widgets,
             'ui_text': {ui.dbConnectButton: 'Disconnect',
                         ui.dbStatusLabel: 'Connected'},
             'children': [{'name': 'empty', 'ui_enable': ui.dbInitButton},
                          {'name': 'initialized',
                           'ui_disable': ui.dbInitButton}]}])


class ApplicationSettingsWindow(SettingsWindow,
                                UiForm('appsettingswindow.ui')):
    """
    RAMSIS specific local application settings window

    The application settings window allows the user to view and modify local
    application settings such as the DB connection credentials. The window
    also provides UI facilities to test and establish the DB connection and
    initialize a fresh application DB.
    """

    def __init__(self, app, **kwargs):
        """
        Application settings window initializer

        :param app: A reference to the application top level object
        :type core: RAMSIS.application.Application
        :param dict kwargs: Additional arguments to pass to the window ctor
        """
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)
        self.app = app

        # State machines for DB settings and buttons
        self._ui_state_machine_db = DbUiStateMachine(self.ui)

        for text, member in (('Real-Time Mode', LaunchMode.REAL_TIME),
                             ('Lab Mode', LaunchMode.LAB)):
            self.ui.launchModeComboBox.addItem(text, member.value)

        # Add new settings here. This maps each user editable settings key to
        # it's corresponding widget in the settings window
        settings_widget_map = {
            # Database settings
            'database/url': self.ui.dbUrlEdit,
            'database/user': self.ui.dbUserEdit,
            'database/name': self.ui.dbNameEdit,
            'database/password': self.ui.dbPasswordEdit,
            'launch_mode': self.ui.launchModeComboBox,
            # Lab mode settings
            'simulation/max_speed': self.ui.simulateMaxRadioButton,
            'simulation/speed': self.ui.speedBox,
        }
        self.register_widgets(settings_widget_map)

        self.start_observing_changes()
        self.load_settings()
        if self.app.ramsis_core.store:
            self._check_db_state()
        else:
            self.validate_db_edits(None)

    def load_settings(self):
        """
        Load the current settings from the settings object and reflect the
        values in the GUI.

        """
        for key, value in self.app.app_settings.all().items():
            widget = self.widget_map.get(key)
            if widget is not None:
                control_interface(widget).set_value(value)

    def action_setting_changed(self):
        widget = self.sender()
        value = control_interface(widget).get_value()
        if value is None:
            return
        key = self.key_map[widget]
        self.app.app_settings[key] = value

    # UI Signal Slots

    @pyqtSlot(name='on_dbConnectButton_clicked')
    def connect_to_db(self):
        if self._ui_state_machine_db.is_disconnected_valid():
            url = self.ui.dbUrlEdit.text()
            db_name = self.ui.dbNameEdit.text()
            user = self.ui.dbUserEdit.text()
            password = self.ui.dbPasswordEdit.text()
            protocol, address = url.split('://')
            db_url = f'{protocol}://{user}:{password}@{address}/{db_name}'
            success = self.app.ramsis_core.connect(db_url)
            if success:
                if self.app.ramsis_core.store.is_empty():
                    self._ui_state_machine_db.to_connected_empty()
                else:
                    self._ui_state_machine_db.to_connected_initialized()
            else:
                QMessageBox.critical(self, 'Connection Failed',
                                     f'Connection to {url} failed. Check the '
                                     f'logs for further information.')
                self._ui_state_machine_db.to_disconnected_valid()
        elif self._ui_state_machine_db.is_connected(allow_substates=True):
            self.app.ramsis_core.disconnect()
            self._ui_state_machine_db.to_disconnected_valid()

    @pyqtSlot(name='on_dbInitButton_clicked')
    def action_init_db(self):
        choice = QMessageBox.information(
            self, 'Init DB',
            'By continuing, the target database will be  initialized with all '
            'the tables required by RT-RAMSIS. Note the target db needs to '
            'have the postgis extension installed.',
            QMessageBox.Ok | QMessageBox.Cancel)
        if choice == QMessageBox.Ok:
            success = self.app.ramsis_core.store.init_db()
            if success:
                self._ui_state_machine_db.to_connected_initialized()
            else:
                QMessageBox.critical(self, 'Initialization Failed',
                                     f'DB initialization failed. Check the '
                                     f'logs for further information.')

    @pyqtSlot(str, name='on_dbUrlEdit_textChanged')
    @pyqtSlot(str, name='on_dbNameEdit_textChanged')
    @pyqtSlot(str, name='on_dbUserEdit_textChanged')
    @pyqtSlot(str, name='on_dbPasswordEdit_textChanged')
    def validate_db_edits(self, *_):
        valid = bool(self.ui.dbUrlEdit.text() and self.ui.dbUserEdit.text()
                     and self.ui.dbPasswordEdit.text()
                     and self.ui.dbNameEdit.text())
        # Note: edits are disabled when connected so we only need to cover
        # the state transitions below.
        if valid:
            self._ui_state_machine_db.to_disconnected_valid()
        else:
            self._ui_state_machine_db.to_disconnected_invalid()

    @pyqtSlot(int, name='on_launchModeComboBox_currentIndexChanged')
    def enable_lab_mode_section(self, idx):
        mode = LaunchMode(self.ui.launchModeComboBox.currentData())
        self.ui.labModeGroupBox.setEnabled(mode == LaunchMode.LAB)

    # Helpers

    def _check_db_state(self):
        if self.app.ramsis_core.store.is_db_initialized():
            self._ui_state_machine_db.to_connected_initialized()
        else:
            self._ui_state_machine_db.to_connected_empty()


class ProjectSettingsWindow(SettingsWindow):

    def __init__(self, project, **kwargs):
        super(ProjectSettingsWindow, self).__init__()
        self.logger = logging.getLogger(__name__)
        self.project = project

        # Other windows
        self.rj_model_configuration_window = None
        self.etas_model_configuration_window = None

        # Setup the user interface
        self.ui = Ui_ProjectSettingsWindow()
        self.ui.setupUi(self)

        # Add new settings here. This maps each user editable settings key to
        # it's corresponding widget in the settings window
        widget_map = {
            'fdsnws_enable': self.ui.enableFdsnCheckBox,
            'fdsnws_url': self.ui.fdsnUrlEdit,
            'hydws_enable': self.ui.enableHydwsCheckBox,
            'hydws_url': self.ui.hydwsUrlEdit,
            'auto_schedule_enable': self.ui.enableAutoSchedulingCheckBox,
            'forecast_interval': self.ui.forecastIntervalBox,
            'forecast_length': self.ui.forecastBinTimeBox,
            'forecast_start': self.ui.firstForecastBox,
            'seismic_rate_interval': self.ui.rateIntervalBox,
            'write_fc_results_to_disk': self.ui.writeResultsToFileCheckBox,
        }
        self.register_widgets(widget_map)

        # Hook up buttons
        self.ui.saveButton.clicked.connect(self.action_save)
        self.ui.cancelButton.clicked.connect(self.action_cancel)
        self.ui.selectOutputDirButton.clicked.\
            connect(self.action_select_output_directory)
        self.ui.resetToDefaultButton.clicked.connect(self.action_load_defaults)
        self.ui.rjConfigButton.clicked.connect(
            self.action_show_rj_model_configuration)
        self.ui.etasConfigButton.clicked.connect(
            self.action_show_etas_model_configuration)

        # Hook up checkboxes
        self.ui.enableRjCheckBox.clicked.connect(self.action_rj_checked)
        self.ui.enableEtasCheckBox.clicked.connect(self.action_etas_checked)

        self.start_observing_changes()
        self.load_settings()

    def load_settings(self):
        """
        Load the current settings from the settings object and reflect the
        values in the GUI.

        """
        for key in self.project.settings.keys():
            widget = self.widget_map.get(key)
            if widget is not None:
                value = self.project.settings[key]
                control_interface(widget).set_value(value)
        # Project properties are shown in the settings tab too
        self.ui.projectTitleEdit.setText(self.project.title)
        local = utc_to_local(self.project.start_date)
        self.ui.projectStartEdit.setDateTime(local)
        local = utc_to_local(self.project.end_date)
        self.ui.projectEndEdit.setDateTime(local)
        self.ui.descriptionEdit.setPlainText(self.project.description)
        ref = self.project.reference_point
        self.ui.refLatEdit.setText('{:.6f}'.format(ref['lat']))
        self.ui.refLonEdit.setText('{:.6f}'.format(ref['lon']))
        self.ui.refHEdit.setText('{:.1f}'.format(ref['h']))

    def action_setting_changed(self):
        widget = self.sender()
        value = control_interface(widget).get_value()
        if value is None:
            return
        key = self.key_map[widget]
        self.project.settings[key] = value

    # Button actions

    def action_select_output_directory(self):
        pass

    def action_load_defaults(self):
        self.settings.register_default_settings()
        self.load_settings()

    def action_save(self):
        p = self.project
        p.title = self.ui.projectTitleEdit.text()
        start_date = pyqt_local_to_utc_ua(self.ui.projectStartEdit.dateTime())
        end_date = pyqt_local_to_utc_ua(self.ui.projectEndEdit.dateTime())
        if start_date != p.start_date or end_date != p.end_date:
            p.start_date = start_date
            p.end_date = end_date
            p.settings['forecast_start'] = p.start_date
            p.update_project_time(p.start_date)
        p.description = self.ui.descriptionEdit.toPlainText()
        try:
            p.reference_point = {'lat': float(self.ui.refLatEdit.text()),
                                 'lon': float(self.ui.refLonEdit.text()),
                                 'h': float(self.ui.refHEdit.text())}
        except TypeError as e:
            self.logger.error('Invalid reference point: {}'.format(e))
        p.settings.commit()
        p.save()
        self.close()

    def action_show_rj_model_configuration(self):
        if self.rj_model_configuration_window is None:
            self.rj_model_configuration_window = ModelConfigurationWindow(
                project=self.project, model='rj')
        self.rj_model_configuration_window.show()

    def action_show_etas_model_configuration(self):
        if self.etas_model_configuration_window is None:
            self.etas_model_configuration_window = ModelConfigurationWindow(
                project=self.project, model='etas')
        self.etas_model_configuration_window.show()

    def action_rj_checked(self):
        state = self.ui.enableRjCheckBox.checkState()
        if state:
            self.ui.rjConfigButton.setEnabled(True)
        else:
            self.ui.rjConfigButton.setDisabled(True)

    def action_etas_checked(self):
        state = self.ui.enableEtasCheckBox.checkState()
        if state:
            self.ui.etasConfigButton.setEnabled(True)
        else:
            self.ui.etasConfigButton.setDisabled(True)
