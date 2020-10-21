# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
General tab facilitites.
"""

from PyQt5.QtCore import QObject
from .tabs import TabPresenter
from .stagewidget import StageWidget
from .tlwidget import TrafficLightWidget

from ramsis.datamodel.forecast import EStage
from RAMSIS.core.reset_stages import reset_stage


class GeneralTabPresenter(TabPresenter):
    """
    Handles the Hazard tabs content

    """

    def __init__(self, ui):
        super().__init__(ui)
        self.status_presenter = StageStatusPresenter(ui)

    def refresh(self, scenario=None, store=None):
        if scenario:
            t = scenario.forecast.starttime
            t_str = t.strftime('%d-%m-%Y %H:%M')
            title = 'Forecast {}    {}'.format(t_str, scenario.name)
        else:
            title = 'Nothing selected'
            scenario = self.scenario
        self.ui.scenarioTitleLabel.setText(title)
        self.refresh_status(scenario, store)

    def refresh_status(self, scenario, store):
        self.status_presenter.refresh_status(scenario, store)


class StageStatusPresenter(QObject):
    """
    Handles the presentation of the forecasts current status

    """

    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self.refresh_methods = []
        self.hazard_reset_button_connected = False
        self.store = None
        self.scenario = None

        # Add stage status widgets
        container_widget = self.ui.stageStatusWidget
        self.stages_config = [
            (EStage.SEISMICITY, '_refresh_model_status',
             'Forecast Stage'),
            # (EStage.SEISMICITY_SKILL,
            # '_refresh_skill_status', 'Skill Stage'),
            (EStage.HAZARD, '_refresh_hazard_status',
             'Hazard Stage'),
            (EStage.RISK, '_refresh_risk_status', 'Risk Stage')]
        self.widgets = {}
        for stage, widget_method, title in self.stages_config:
            self.widgets[stage] = StageWidget(title, parent=container_widget)

        # Add traffic light widget
        self.tlWidget = TrafficLightWidget(parent=self.ui.tlWidget)
        self.move_widgets()

    def move_widgets(self):
        for i, widget in enumerate(self.widgets.values()):
            widget.move(i * (widget.size().width() - 18), 0)

    def refresh_status(self, scenario, store):
        """
        Show the updated status of an ongoing calculation

        :param Scenario scenario: Scenario of which to present the status

        """
        if scenario is None:
            return
        self.scenario = scenario
        self.store = store
        self.refresh_methods = []
        container_widget = self.ui.stageStatusWidget
        for stage, widget_method, title in self.stages_config:
            try:
                scenario_stage = self.scenario[stage]
                if stage not in self.widgets.keys():
                    self.widgets[stage] = StageWidget(
                        title, parent=container_widget)
                widget = self.widgets[stage]
                if scenario_stage.enabled:
                    widget.set_stage_status(scenario_stage.status.state.name)
                else:
                    widget.set_stage_status('DISABLED')
                self.refresh_methods.append(widget_method)
            except KeyError:
                if stage not in self.widgets.keys():
                    del self.widgets[stage]
                pass

        self.move_widgets()

        for method in self.refresh_methods:
            getattr(self, method)()

    def _refresh_model_status(self):
        widget = self.widgets[EStage.SEISMICITY]
        widget.clear_substages()

        try:
            stage = self.scenario[EStage.SEISMICITY]
        except KeyError:
            return

        # model runs
        config = {}
        for run in stage.runs:
            if run.enabled:
                config[run.model.name] = str(run.status.state.name)
            else:
                config[run.model.name] = 'DISABLED'
        widget.set_substages(list(config.items()))

    def _refresh_skill_status(self):
        raise NotImplementedError("Seismicity Skill stage status"
                                  "is not implemented")

    def _refresh_hazard_status(self):
        widget = self.widgets[EStage.HAZARD]
        widget.clear_substages()

        try:
            stage = self.scenario[EStage.HAZARD]
        except KeyError:
            widget.disable()
            return
        if not stage.enabled:
            widget.disable()
            return
        # stage status and count of runs in states
        config = {'COMPLETE': 0,
                  'PENDING': 0,
                  'RUNNING': 0,
                  'ERROR': 0,
                  'DISPATCHED': 0,
                  'PREPARED': 0}

        for run in stage.runs:
            # Do not expect disabled runs to exist for hazard.
            if run.enabled:
                status = str(run.status.state.name)
                try:
                    config[status] += 1
                except KeyError:
                    pass

        widget.set_aggregate_substages(list(config.items()))
        widget.ui.stageReset.show()
        if not self.hazard_reset_button_connected:
            widget.ui.stageReset.clicked.connect(self._refresh_hazard_reset)
            self.hazard_reset_button_connected = True

    def _refresh_hazard_reset(self):
        self.scenario = reset_stage(
            self.scenario, self.store, stage=EStage.HAZARD)
        self._refresh_hazard_status()

    def _refresh_risk_status(self):
        pass

    def _refresh_traffic_light(self):
        raise NotImplementedError("Traffic light not implemented")
        # TODO: implement
        try:
            status = self.scenario.forecast_result.risk_result.status
        except Exception:
            self.tlWidget.off()
        else:
            if status.finished:
                self.tlWidget.green()
            else:
                self.tlWidget.off()
