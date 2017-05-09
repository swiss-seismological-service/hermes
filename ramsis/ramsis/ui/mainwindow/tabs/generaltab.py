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

        self.widgets[0].set_substages([
            ('Reasenberg-Jones', 'running...'),
            ('Shapiro (spatial)', 'disabled'),
            ('Ollinger-Gischig', 'running...')
        ])
        self.widgets[0].set_status('running')

    def present_status(self, status):
        """
        Show the updated status of an ongoing calculation

        :param CalculationStatus status: 

        """
        if status is None:
            return
        # determine the stage
        if status.model_result:
            widget = self.widgets[0]
        elif status.hazard_result:
            widget = self.widgets[1]
        else:
            widget = self.widgets[2]
        widget.set_status(status.state)


