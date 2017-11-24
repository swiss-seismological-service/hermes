# -*- encoding: utf-8 -*-
"""
Presentation classes for each of the tabs shown in the main area of the
forecast window
    
Copyright (C) 2016, SED (ETH Zurich)

"""

import logging
from PyQt5.QtCore import QObject


class TabPresenter(QObject):
    """
    Handles a tabs content

    This is an abstract class

    """
    def __init__(self, ui):
        """
        :param ui: reference to the Qt UI
        :type ui: Ui_ForecastsWindow

        """
        super(TabPresenter, self).__init__()
        self.ui = ui
        self.scenario = None
        self.logger = logging.getLogger(__name__)

    def present_scenario(self, scenario):
        """
        Show input or results for a scenario

        We also listen to changes to the currently displayed result to update
        the tabs content accordingly

        :param Scenario scenario: forecast scenario

        """
        if self.scenario:
            self.scenario.scenario_changed.disconnect(self._on_change)
        self.scenario = scenario
        if self.scenario:
            self.scenario.scenario_changed.connect(self._on_change)
        self.refresh()

    def refresh(self):
        raise NotImplementedError("Please Implement this method")

    def _on_change(self, obj):
        self.refresh()







