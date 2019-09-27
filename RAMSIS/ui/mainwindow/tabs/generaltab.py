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
        super(GeneralTabPresenter, self).__init__(ui)
        self.status_presenter = StageStatusPresenter(ui)

    def refresh(self):
        if self.scenario:
            t = self.scenario.forecast.starttime
            t_str = utc_to_local(t).strftime('%d.%m.%Y %H:%M')
            title = 'Forecast {}    {}'.format(t_str, self.scenario.name)
        else:
            title = 'Nothing selected'
        self.ui.scenarioTitleLabel.setText(title)
        self.refresh_status()

    def refresh_status(self):
        self.status_presenter.refresh_status(self.scenario)


class StageStatusPresenter(QObject):
    """
    Handles the presentation of the forecasts current status

    """

    def __init__(self, ui):
        super(StageStatusPresenter, self).__init__()
        self.ui = ui

        # Add stage status widgets
        container_widget = self.ui.stageStatusWidget
        self.widgets = [
            StageWidget('Forecast Stage', parent=container_widget),
            StageWidget('Hazard Stage', parent=container_widget),
            StageWidget('Risk Stage', parent=container_widget)
        ]

        # Add traffic light widget
        self.tlWidget = TrafficLightWidget(parent=self.ui.tlWidget)

        for i, widget in enumerate(self.widgets):
            widget.move(i * (widget.size().width() - 18), 0)

    def refresh_status(self, scenario):
        """
        Show the updated status of an ongoing calculation

        :param Scenario scenario: Scenario of which to present the status

        """
        if scenario is None:
            return
        # TODO LH: reimplement with new model
        self._refresh_model_status(scenario)
        # self._refresh_hazard_status(scenario)
        # self._refresh_risk_status(scenario)
        # self._refresh_traffic_light(scenario)

    def _refresh_model_status(self, scenario):
        widget = self.widgets[0]
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
                continue
            config[run.model.name] = 'Disabled'

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

    def _refresh_hazard_status(self, scenario):
        widget = self.widgets[1]
        if not scenario.config['run_hazard']:
            widget.disable()
        else:
            result = scenario.forecast_result
            if result is None or result.hazard_result is None:
                widget.plan()
            else:
                status = scenario.forecast_result.hazard_result.status
                widget.set_state(status.state)

    def _refresh_risk_status(self, scenario):
        widget = self.widgets[2]
        if not scenario.config['run_risk']:
            widget.disable()
        else:
            result = scenario.forecast_result
            if result is None or result.risk_result is None:
                widget.plan()
            else:
                status = scenario.forecast_result.risk_result.status
                widget.set_state(status.state)

    def _refresh_traffic_light(self, scenario):
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
