# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
General tab facilitites.
"""

from PyQt5.QtCore import QObject
from .tabs import TabPresenter
from .stagewidget import StageWidget
from .tlwidget import TrafficLightWidget

from ramsis.datamodel.forecast import EStage
from RAMSIS.ui.base.utils import utc_to_local


class GeneralTabPresenter(TabPresenter):
    """
    Handles the Hazard tabs content

    """

    def __init__(self, ui):
        super().__init__(ui)
        self.status_presenter = StageStatusPresenter(ui)

    def refresh(self, scenario=None):
        if scenario:
            t = scenario.forecast.starttime
            t_str = utc_to_local(t).strftime('%d.%m.%Y %H:%M')
            title = 'Forecast {}    {}'.format(t_str, scenario.name)
        else:
            title = 'Nothing selected'
            scenario = self.scenario
        self.ui.scenarioTitleLabel.setText(title)
        self.refresh_status(scenario)

    def refresh_status(self, scenario):
        self.status_presenter.refresh_status(scenario)


class StageStatusPresenter(QObject):
    """
    Handles the presentation of the forecasts current status

    """

    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self.refresh_methods = []

        # Add stage status widgets
        container_widget = self.ui.stageStatusWidget
        self.stages_config = [(EStage.SEISMICITY, '_refresh_model_status', 'Forecast Stage'),
                  #(EStage.SEISMICITY_SKILL, '_refresh_skill_status', 'Skill Stage'),
                  (EStage.HAZARD, '_refresh_hazard_status', 'Hazard Stage'),
                  (EStage.RISK, '_refresh_risk_status', 'Risk Stage')]
        self.widgets = {}
        for stage, widget_method, title in self.stages_config:
            self.widgets[stage] = StageWidget(title, parent=container_widget)


        #self.widgets = [
        #    StageWidget('Forecast Stage', parent=container_widget),
        #    StageWidget('Hazard Stage', parent=container_widget),
        #    StageWidget('Risk Stage', parent=container_widget)
        #]

        # Add traffic light widget
        self.tlWidget = TrafficLightWidget(parent=self.ui.tlWidget)
        self.move_widgets()

    def move_widgets(self):
        for i, widget in enumerate(self.widgets.values()):
            widget.move(i * (widget.size().width() - 18), 0)

    def refresh_status(self, scenario):
        """
        Show the updated status of an ongoing calculation

        :param Scenario scenario: Scenario of which to present the status

        """
        if scenario is None:
            return
        self.refresh_methods = []
        container_widget = self.ui.stageStatusWidget
        for stage, widget_method, title in self.stages_config:
            try:
                scenario_stage = scenario[stage]
                if not stage in self.widgets.keys():
                    self.widgets[stage] = StageWidget(title, parent=container_widget)
                widget = self.widgets[stage]
                if scenario_stage.enabled:
                    widget.set_stage_status(scenario_stage.status.state.name)
                else:
                    widget.set_stage_status('DISABLED')
                self.refresh_methods.append(widget_method)
            except KeyError:
                if stage in self.widgets.keys():
                    del self.widgets[stage]
                pass

        self.move_widgets()

        for method in self.refresh_methods:
            getattr(self, method)(scenario)

    def _refresh_model_status(self, scenario):
        widget = self.widgets[EStage.SEISMICITY]
        widget.clear_substages()

        try:
            stage = scenario[EStage.SEISMICITY]
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


        # TODO LH: revisit overall state
        # if all(s in (EStatus.COMPLETE, 'Disabled') for s in config.values()):
        #    state = EStatus.COMPLETE
        #    widget.set_state(state)
        # if all(s in (CS.COMPLETE, 'Disabled') for s in substages.values()):
        #     state = CS.COMPLETE
        # elif any(s == CS.ERROR for s in substages.values()):
        #     state = CS.ERROR
        # elif any(s == CS.RUNNING for s in substages.values()):
        #     state = CS.RUNNING
        # else:
        #     widget.plan()
        #     return
        # widget.set_state(state)

    def _refresh_skill_status(self, scenario):
        raise NotImplementedError("Seismicity Skill stage status"
                                   "is not implemented")

    def _refresh_hazard_status(self, scenario):
        widget = self.widgets[EStage.HAZARD]
        widget.clear_substages()

        try:
            stage = scenario[EStage.HAZARD]
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
                  'PREPARED': 0}

        for run in stage.runs:
            # Do not expect disabled runs to exist for hazard.
            if run.enabled:
                status = str(run.status.state.name)
                try:
                    config[status] += 1
                except KeyError as err:
                    pass

        widget.set_aggregate_substages(list(config.items()))

    def _refresh_risk_status(self, scenario):
        widget = self.widgets[EStage.RISK]
        return

    def _refresh_traffic_light(self, scenario):
        raise NotImplementedError("Traffic light not implemented")
        # TODO: implement
        try:
            status = scenario.forecast_result.risk_result.status
        except Exception:
            self.tlWidget.off()
        else:
            if status.finished:
                self.tlWidget.green()
            else:
                self.tlWidget.off()
