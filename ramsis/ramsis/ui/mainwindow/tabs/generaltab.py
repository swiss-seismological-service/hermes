# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2015, SED (ETH Zurich)

"""

from PyQt4.QtCore import QObject
from tabs import TabPresenter
from stagewidget import StageWidget
from ui.ramsisuihelpers import utc_to_local
from ramsisdata.calculationstatus import CalculationStatus as CS


class GeneralTabPresenter(TabPresenter):
    """
    Handles the Hazard tabs content

    """

    def __init__(self, ui):
        super(GeneralTabPresenter, self).__init__(ui)
        self.status_presenter = StageStatusPresenter(ui)

    def refresh(self):
        if self.scenario:
            t = self.scenario.forecast_input.forecast.forecast_time
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
        self.container_widget = self.ui.stageStatusWidget

        self.widgets = [
            StageWidget('Forecast Stage', parent=self.container_widget),
            StageWidget('Hazard Stage', parent=self.container_widget),
            StageWidget('Risk Stage', parent=self.container_widget)
        ]

        for i, widget in enumerate(self.widgets):
            widget.move(i * (widget.size().width() - 18), 0)

    def refresh_status(self, scenario):
        """
        Show the updated status of an ongoing calculation

        :param Scenario scenario: Scenario of which to present the status

        """
        if scenario is None:
            return
        self._refresh_model_status(scenario)
        self._refresh_hazard_status(scenario)
        self._refresh_risk_status(scenario)

    def _refresh_model_status(self, scenario):
        widget = self.widgets[0]
        widget.clear_substages()
        if not scenario.config['run_is_forecast']:
            widget.disable()
            return
        # substages
        project = scenario.forecast_input.forecast.forecast_set.project
        models = project.settings['forecast_models']
        substages = {m: 'Planned' for m in models}
        for key in substages.keys():
            if key in scenario.config['disabled_models']:
                substages[key] = 'Disabled'
        if scenario.forecast_result:
            for model_id, mr in scenario.forecast_result.model_results.items():
                if mr.status:
                    substages[model_id] = mr.status.state
        widget.set_substages([(models[k]['title'], v)
                              for k, v in substages.items()])
        # revisit overall state
        if all(s in (CS.COMPLETE, 'Disabled') for s in substages.values()):
            state = CS.COMPLETE
        elif any(s == CS.ERROR for s in substages.values()):
            state = CS.ERROR
        elif any(s == CS.RUNNING for s in substages.values()):
            state = CS.RUNNING
        else:
            widget.plan()
            return
        widget.set_state(state)

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


