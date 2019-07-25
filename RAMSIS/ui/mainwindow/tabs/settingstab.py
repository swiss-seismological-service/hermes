# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Configuration tab related GUI facilities.
"""

from PyQt5.QtCore import Qt

from .tabs import TabPresenter
from RAMSIS.ui.dialog import ImportInjectionStrategyFromFileDialog


class SettingsTabPresenter(TabPresenter):
    """
    Present the main window's scenario configuration tab content.
    """
    # TODO(damb): How to store injection plan if 'constant values' would have
    # been chosen. -> As a consequence, the injection plan would be generated
    # on-the-fly i.e. when the forecast is actually executed.

    def __init__(self, ui):
        super().__init__(ui)
        self.config_map = {
            self.ui.fcStageEnable: 'run_is_forecast',
            self.ui.hazardStageEnable: 'run_hazard',
            self.ui.riskStageEnable: 'run_risk'
        }

        for checkbox in self.config_map.keys():
            checkbox.stateChanged.connect(self.on_check_state_changed)

        self.ui.fcStageEnable.stateChanged.connect(
            self.on_forecast_stage_state_changed)

        self.injection_strategy_rbtns = (
            self.ui.injectionStrategyRadioButton1, )

        for rb in self.injection_strategy_rbtns:
            rb.toggled.connect(
                self.on_injection_strategy_rbtn_state_changed)

        self.ui.injectionStrategyImportFromFilePushButton.clicked.\
            connect(self.on_import_from_file_btn_click)

        self.fc_stage_widgets = (
            self.ui.injectionStrategyRadioButton1,
            self.ui.injectionStrategyImportFromFilePushButton,
            self.ui.injectionStrategyLabel, )

    def refresh(self):
        # TODO LH: adapt to new model
        pass
        # if self.scenario:
        #     config = self.scenario.config
        #     for checkbox, config_name in self.config_map.items():
        #         checkbox.setCheckState(Qt.Checked if config[config_name] else
        #                                Qt.Unchecked)

    def on_check_state_changed(self, state):
        sender = self.sender()
        if sender not in self.config_map:
            return
        key = self.config_map[sender]
        self.scenario.config[key] = True if state == Qt.Checked else False
        self.scenario.scenario_changed.emit(self.scenario.config)
        self.scenario.project.save()

    def on_forecast_stage_state_changed(self, state):
        sender = self.sender()
        if sender != self.ui.fcStageEnable:
            return
        state = True if state == Qt.Checked else False

        for w in self.fc_stage_widgets:
            w.setEnabled(state)

    def on_injection_strategy_rbtn_state_changed(self):
        self.ui.injectionStrategyImportFromFilePushButton.setEnabled(False)

        if self.ui.injectionStrategyRadioButton1.isChecked():
            self.ui.injectionStrategyImportFromFilePushButton.setEnabled(True)

    def on_import_from_file_btn_click(self):
        import_dialog = ImportInjectionStrategyFromFileDialog(
            parent=self.ui.centralWidget)
        import_dialog.exec_()
        import_dialog.data
