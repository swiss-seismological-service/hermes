# -*- encoding: utf-8 -*-
"""
Controller class for the settings window
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import logging

from PyQt4 import QtGui
from views.ui_settingswindow import Ui_SettingsWindow
import atlssettings


class SettingsWindow(QtGui.QDialog):

    def __init__(self, settings, **kwargs):
        QtGui.QDialog.__init__(self, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.settings = settings

        # Setup the user interface
        self.ui = Ui_SettingsWindow()
        self.ui.setupUi(self)

        # Add new settings here. This maps each user editable settings key to
        # it's corresponding widget in the settings window
        self.widget_map = {
            # General settings
            'open_last_project':            self.ui.openLastProjectOnStartup,
            'enable_lab_mode':              self.ui.enableLabModeCheckBox,
            # Forecast core settings
            'core/write_results_to_disk': self.ui.writeResultsToFileCheckBox,
            'core/fc_interval':           self.ui.forecastIntervalBox,
            'core/fc_bin_size':           self.ui.forecastBinTimeBox,
            'core/rt_interval':           self.ui.rateIntervalBox,
            'core/num_fc_bins':           self.ui.forecastBinNoBox,
            # Lab mode settings
            'lab_mode/infinite_speed':      self.ui.simulateAFAPRadioButton,
            'lab_mode/speed':               self.ui.speedBox,
        }
        # Invert the mapping for reverse lookups when values change
        self.key_map = dict((v, k) for k, v in self.widget_map.items())

        # Hook up buttons
        self.ui.okButton.clicked.connect(self.action_ok)
        self.ui.selectOutputDirButton.clicked.\
            connect(self.action_select_output_directory)
        self.ui.resetToDefaultButton.clicked.connect(self.action_load_defaults)

        self.start_observing_changes()
        self.load_settings(self.settings)

    def start_observing_changes(self):
        """ Observe changes on all settings widgets """
        for widget in self.widget_map.values():
            signal = self._change_signal_for_widget(widget)
            if signal is None:
                continue
            signal.connect(self.action_setting_changed)

    def load_settings(self, settings):
        """
        Load the current settings from the settings object and reflect the
        values in the GUI.

        """
        for key in atlssettings.known_settings:
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
        else:
            self.logger.error('Getting value from' + str(widget) +
                              'failed because the corresponding Qt '
                              'widget type is not yet supported.')
            return None