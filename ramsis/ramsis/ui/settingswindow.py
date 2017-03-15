# -*- encoding: utf-8 -*-
"""
Controller class for the settings window

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import logging
import os

from PyQt4 import QtGui, uic
import ramsissettings

ui_path = os.path.dirname(__file__)
APPLICATION_SETTINGS_WINDOW_PATH = \
    os.path.join(ui_path, 'views', 'appsettingswindow.ui')
Ui_ApplicationSettingsWindow = \
    uic.loadUiType(APPLICATION_SETTINGS_WINDOW_PATH)[0]
PROJECT_SETTINGS_WINDOW_PATH = \
    os.path.join(ui_path, 'views', 'projectsettingswindow.ui')
Ui_ProjectSettingsWindow = \
    uic.loadUiType(PROJECT_SETTINGS_WINDOW_PATH)[0]


class SettingsWindow(QtGui.QDialog):

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
            signal = self._change_signal_for_widget(widget)
            if signal is None:
                continue
            signal.connect(self.action_setting_changed)

    # Private Helper Methods

    def _change_signal_for_widget(self, widget):
        if widget.inherits('QCheckBox'):
            return widget.stateChanged
        elif widget.inherits('QRadioButton'):
            return widget.toggled
        elif widget.inherits('QSpinBox'):
            return widget.valueChanged
        elif widget.inherits('QDoubleSpinBox'):
            return widget.valueChanged
        elif widget.inherits('QDateTimeEdit'):
            return widget.dateTimeChanged
        elif widget.inherits('QLineEdit'):
            return widget.textChanged
        else:
            self.logger.error('Setting value for' + str(widget) +
                              'failed because the corresponding Qt '
                              'widget type is not yet supported.')
        return None

    def _set_value_in_widget(self, value, widget):
        if widget.inherits('QAbstractButton'):
            widget.setChecked(value)
        elif widget.inherits('QSpinBox'):
            widget.setValue(value)
        elif widget.inherits('QDoubleSpinBox'):
            widget.setValue(value)
        elif widget.inherits('QDateTimeEdit'):
            widget.setDateTime(value)
        elif widget.inherits('QLineEdit'):
            widget.setText(value)
        else:
            self.logger.error('Setting value for' + str(widget) +
                              'failed because the corresponding Qt '
                              'widget type is not yet supported.')

    def _value_for_widget(self, widget):
        if widget.inherits('QAbstractButton'):
            return widget.isChecked()
        elif widget.inherits('QSpinBox'):
            return widget.value()
        elif widget.inherits('QDoubleSpinBox'):
            return widget.value()
        elif widget.inherits('QDateTimeEdit'):
            return widget.dateTime().toPyDateTime()
        elif widget.inherits('QLineEdit'):
            return widget.text()
        else:
            self.logger.error('Getting value from' + str(widget) +
                              'failed because the corresponding Qt '
                              'widget type is not yet supported.')
            return None


class ApplicationSettingsWindow(SettingsWindow):

    def __init__(self, settings, **kwargs):
        QtGui.QDialog.__init__(self, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.settings = settings

        # Setup the user interface
        self.ui = Ui_ApplicationSettingsWindow()
        self.ui.setupUi(self)

        # Add new settings here. This maps each user editable settings key to
        # it's corresponding widget in the settings window
        widget_map = {
            # General settings
            'enable_lab_mode': self.ui.enableLabModeCheckBox,
            # Lab mode settings
            'lab_mode/infinite_speed': self.ui.simulateAFAPRadioButton,
            'lab_mode/speed': self.ui.speedBox,
        }
        self.register_widgets(widget_map)

        # Hook up buttons
        self.ui.saveButton.clicked.connect(self.action_ok)
        self.ui.selectOutputDirButton.clicked.\
            connect(self.action_select_output_directory)
        self.ui.resetToDefaultButton.clicked.connect(self.action_load_defaults)

        self.start_observing_changes()
        self.load_settings()

    def load_settings(self):
        """
        Load the current settings from the settings object and reflect the
        values in the GUI.

        """
        for key in ramsissettings.known_settings:
            widget = self.widget_map.get(key)
            if widget is not None:
                value = self.settings.value(key)
                self._set_value_in_widget(value, widget)

    def action_setting_changed(self):
        widget = self.sender()
        value = self._value_for_widget(widget)
        if value is None:
            return
        key = self.key_map[widget]
        self.settings.set_value(key, value)

    # Button actions

    def action_select_output_directory(self):
        pass

    def action_load_defaults(self):
        self.settings.register_default_settings()
        self.load_settings(self.settings)

    def action_ok(self):
        self.close()


class ProjectSettingsWindow(SettingsWindow):

    def __init__(self, project, **kwargs):
        super(ProjectSettingsWindow, self).__init__()
        self.logger = logging.getLogger(__name__)
        self.project = project

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
                self._set_value_in_widget(value, widget)
        # Project properties are shown in the settings tab too
        self.ui.projectTitleEdit.setText(self.project.title)
        self.ui.projectStartEdit.setDateTime(self.project.start_date)
        self.ui.projectEndEdit.setDateTime(self.project.end_date)
        self.ui.descriptionEdit.setPlainText(self.project.description)
        ref = self.project.reference_point
        self.ui.refLatEdit.setText('{:.6f}'.format(ref['lat']))
        self.ui.refLonEdit.setText('{:.6f}'.format(ref['lon']))
        self.ui.refHEdit.setText('{:.1f}'.format(ref['h']))

    def action_setting_changed(self):
        widget = self.sender()
        value = self._value_for_widget(widget)
        if value is None:
            return
        key = self.key_map[widget]
        self.project.settings[key] = value

    # Button actions

    def action_select_output_directory(self):
        pass

    def action_load_defaults(self):
        self.settings.register_default_settings()
        self.load_settings(self.project.settings)

    def action_save(self):
        p = self.project
        p.title = self.ui.projectTitleEdit.text()
        start_date = self.ui.projectStartEdit.dateTime().toPyDateTime()
        end_date = self.ui.projectEndEdit.dateTime().toPyDateTime()
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
        except TypeError, e:
            self.logger.error('Invalid reference point: {}'.format(e))
        p.settings.commit()
        p.save()
        self.close()
