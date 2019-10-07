# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Presentation classes for each of the tabs shown in the main area of the
forecast window.
"""

import logging

from PyQt5.QtCore import QObject


class TabPresenter(QObject):
    """
    Abstract base class handling tab content
    """

    def __init__(self, ui):
        """
        :param ui: reference to the Qt UI
        :type ui: Ui_ForecastsWindow

        """
        super().__init__()
        self.ui = ui
        self.scenario = None
        self.logger = logging.getLogger(__name__)

    def present_scenario(self, scenario):
        """
        Show input or results for a scenario

        We also listen to changes to the currently displayed result to update
        the tabs content accordingly

        :param scenario: forecast scenario

        """
        # TODO LH: these signals don't exist anymore. find another way
        # if self.scenario:
        #     self.scenario.scenario_changed.disconnect(self._on_change)
        self.scenario = scenario
        # if self.scenario:
        #     self.scenario.scenario_changed.connect(self._on_change)
        self.refresh()

    def refresh(self):
        raise NotImplementedError

    def _on_change(self, obj):
        self.refresh()
