# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2015, SED (ETH Zurich)

"""

from PyQt4.QtCore import QObject
from tabs import TabPresenter
from stagewidget import StageWidget


class GeneralTabPresenter(TabPresenter):
    """
    Handles the Hazard tabs content

    """

    def __init__(self, ui):
        super(GeneralTabPresenter, self).__init__(ui)
        self.status_presenter = StageStatusPresenter(ui)

    def refresh(self):
        if self.scenario:
            t = self.scenario.forecast_input.forecast\
                .forecast_time.strftime('%d.%m.%Y %H:%M')
            title = 'Forecast {}    {}'.format(t, self.scenario.name)
        else:
            title = 'Nothing selected'
        self.ui.scenarioTitleLabel.setText(title)


class StageStatusPresenter(QObject):
    """
    A base class for presenting time lines

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
