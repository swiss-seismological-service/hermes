# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Controller class for the settings window
"""

import logging
import os

from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QDialog, QMessageBox

from RAMSIS.core.controller import LaunchMode
from RAMSIS.ui.base.bindings import (AttrBinding, DictBinding)
from RAMSIS.ui.base.controlinterface import control_interface
from RAMSIS.ui.base.state import UiStateMachine
from RAMSIS.ui.utils import UiForm

ui_path = os.path.dirname(__file__)
PROJECT_SETTINGS_WINDOW_PATH = \
    os.path.join(ui_path, 'views', 'projectsettingswindow.ui')
Ui_ProjectSettingsWindow = \
    uic.loadUiType(
        PROJECT_SETTINGS_WINDOW_PATH,
        import_from='RAMSIS.ui.views', from_imports=True)[0]


class SettingsWindow(QDialog):
    # TODO LH: harmonize initializers, add on-accept callback

    def __init__(self):
        super().__init__()
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
                if self.app.ramsis_core.store.is_db_initialized():
                    self._ui_state_machine_db.to_connected_initialized()
                else:
                    self._ui_state_machine_db.to_connected_empty()
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
        valid = bool(self.ui.dbUrlEdit.text() and
                     self.ui.dbUserEdit.text() and
                     self.ui.dbPasswordEdit.text() and
                     self.ui.dbNameEdit.text())
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

    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.project = project
        self.save_callback = None

        # Other windows
        self.rj_model_configuration_window = None
        self.etas_model_configuration_window = None

        # Setup the user interface
        self.ui = Ui_ProjectSettingsWindow()
        self.ui.setupUi(self)

        # Register bindings
        settings = project.settings
        self.bindings = [
            AttrBinding(project, 'name', self.ui.projectTitleEdit),
            AttrBinding(project, 'description', self.ui.descriptionEdit),
            AttrBinding(project, 'starttime', self.ui.projectStartEdit),
            AttrBinding(project, 'endtime', self.ui.projectEndEdit),
            AttrBinding(project, 'spatialreference', self.ui.proj4Edit),
            AttrBinding(project, 'referencepoint_x', self.ui.refXEdit),
            AttrBinding(project, 'referencepoint_y', self.ui.refYEdit),
            DictBinding(settings, 'fdsnws_enable', self.ui.enableFdsnCheckBox),
            DictBinding(settings, 'fdsnws_url', self.ui.fdsnUrlEdit),
            DictBinding(settings, 'hydws_url', self.ui.hydwsUrlEdit),
            DictBinding(settings, 'hydws_enable', self.ui.enableHydwsCheckBox),
        ]
        self.refresh_ui()

    def refresh_ui(self):
        for binding in self.bindings:
            binding.refresh_ui()

    # Button actions

    @pyqtSlot(name='on_resetToDefaultButton_clicked')
    def action_load_defaults(self):
        self.project.settings.register_default_settings()
        self.refresh_ui()

    @pyqtSlot(name='on_saveButton_clicked')
    def action_save(self):
        self.project.settings.commit()
        if self.save_callback:
            self.save_callback(self.project)
        self.close()

    @pyqtSlot(name='on_cancelButton_clicked')
    def action_cancel(self):
        super().action_cancel()
