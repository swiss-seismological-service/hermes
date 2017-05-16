# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2015, SED (ETH Zurich)

"""

from PyQt4.QtCore import Qt
from tabs import TabPresenter


class SettingsTabPresenter(TabPresenter):
    """
    Handles the Hazard tabs content

    """

    def __init__(self, ui):
        super(SettingsTabPresenter, self).__init__(ui)
        self.config_map = {
            self.ui.fcStageEnable: 'run_is_forecast',
            self.ui.hazardStageEnable: 'run_hazard',
            self.ui.riskStageEnable: 'run_risk'
        }

        for checkbox in self.config_map.keys():
            checkbox.stateChanged.connect(self.on_check_state_changed)

    def refresh(self):
        if self.scenario:
            config = self.scenario.config
            for checkbox, config_name in self.config_map.items():
                checkbox.setCheckState(Qt.Checked if config[config_name] else
                                       Qt.Unchecked)

    def on_check_state_changed(self, state):
        sender = self.sender()
        if sender not in self.config_map:
            return
        key = self.config_map[sender]
        self.scenario.config[key] = True if state == Qt.Checked else False
        self.scenario.scenario_changed.emit(self.scenario.config)
        self.scenario.project.save()


