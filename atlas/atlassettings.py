# -*- encoding: utf-8 -*-
"""
All Atlas settings and their default values are handled from here.
If you add new settings define their default values in the known_settings
variable. If the settings should be accessible from the settings dialog in the
GUI too, make sure you add the corresponding Qt widget to the widget_map in
settingswindow.py

Note that the module expects that the v2 API is used for QVariant (which is
set in the Atlas top level object)
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from PyQt4 import QtCore

# known settings and their default values
known_settings = {
    # General Settings
    'general/recent_files':         None,    # List of recently opened projects (paths)
    'general/open_last_project':    True,    # Open the last project when the app starts
    'general/enable_lab_mode':      True,    # Enable lab mode to simulate through existing data
    # Forecast Engine
    'engine/write_results_to_disk': True,    # Write forecasting results to disk
    'engine/output_directory':      None,    # Output directory for results, if none it writes to the app directory
    'engine/fc_interval':           6.0,     # Forecasting interval [hours]
    'engine/fc_bin_size':           6.0,     # Length of each forecast bin [hours]
    'engine/rt_interval':           1.0,     # Rate computation interval [minutes]
    'engine/num_fc_bins':           6,       # Number of forecast bins
    # Lab mode settings
    'lab_mode/infinite_speed':      True,    # Simulate through catalog as fast as possible
    'lab_mode/speed':               1000,    # Simulation speed (factor), ignored if lab_mode/infinite_speed is True
}


class AppSettings:
    """
    Manages application settings.

    To access settings through this class, make sure the settings key and
    default value are registered in known_settings.

    """

    def __init__(self, settings_file=None):
        """
        Load either the user specific settings or, if a file name is
        provided, specific settings from that file.

        """
        self._settings_file = settings_file
        if settings_file is None:
            self._settings = QtCore.QSettings()
        else:
            self._settings = QtCore.QSettings(settings_file)

    @property
    def settings(self):
        """
        Provides direct access to the underlying QSettings that are used to
        read/store settings values.

        """
        return self._settings

    def value(self, key):
        """
        Returns the value that is stored for key or the default value if
        no value is stored.

        If the key is not known, the function will throw an exception.

        """
        if not key in known_settings.keys():
            raise Exception(key + ' is not a known registered setting')
        default = known_settings[key]
        return self._settings.value(key, defaultValue=default)

    def set_value(self, key, value):
        """
        Sets the value for key

        If the key is not known, the function will throw an exception.

        """
        if not key in known_settings.keys():
            raise Exception(key + ' is not a known registered setting')
        return self._settings.setValue(key, value)

    def register_default_settings(self):
        """
        Writes the default value for each setting to the settings file

        """
        for key, value in known_settings:
            self._settings.setValue(key, value)
        self._settings.sync()

