# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2015, SED (ETH Zurich)

"""

import numpy as np
from .tabs import TabPresenter


class HazardTabPresenter(TabPresenter):
    """
    Handles the Hazard tabs content

    """

    def refresh(self):
        # FIXME: use new data model
        try:
            haz_result = self.scenario.forecast_result.hazard_result
            haz_curves = haz_result.h_curves
        except AttributeError:
            haz_curves = None
            calc_id = None
        else:
            calc_id = haz_result.calc_id

        self.ui.hazCalcIdLabel.setText(str(calc_id) if calc_id else 'N/A')

        self.ui.hCurveWidget.axes.clear()
        if haz_curves:
            imls = haz_curves['IMLs']
            poes = haz_curves['poEs']
            rlz = np.array([poEs for label, poEs in poes.items()
                           if not ('mean' in label or 'quantile' in label)])
            mean = np.array([poEs for label, poEs in poes.items()
                             if 'mean' in label])
            quantile = np.array([poEs for label, poEs in poes.items()
                                 if 'quantile' in label])
            self.ui.hCurveWidget.plot(imls, rlz.T, '.75',
                                      imls, mean.T, 'r',
                                      imls, quantile.T, '-k')
        else:
            self.ui.hCurveWidget.draw()
