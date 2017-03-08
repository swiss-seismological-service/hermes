# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2015, SED (ETH Zurich)

"""

from PyQt4.QtCore import QThread
from tabs import TabPresenter


class GeneralTabPresenter(TabPresenter):
    """
    Handles the Hazard tabs content

    """

    def refresh(self):
        if self.scenario:
            t = self.scenario.forecast_input.forecast\
                .forecast_time.strftime('%d.%m.%Y %H:%M')
            title = 'Forecast {}    {}'.format(t, self.scenario.name)
        else:
            title = 'Nothing selected'
        self.ui.scenarioTitleLabel.setText(title)
