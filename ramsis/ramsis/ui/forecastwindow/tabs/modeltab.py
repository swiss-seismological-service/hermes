# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2015, SED (ETH Zurich)

"""

import numpy as np
from tabs import TabPresenter
from core.engine import ismodelcontrol as mc


class ModelTabPresenter(TabPresenter):
    """
    Handles the Induced Seismicity tabs content

    """
    def __init__(self, ui):
        """
        :param ui: reference to the Qt UI
        :type ui: Ui_ForecastsWindow

        """
        super(ModelTabPresenter, self).__init__(ui)

        # Populate the models chooser combo box
        self.ui.modelSelectorComboBox.currentIndexChanged.connect(
            self.action_model_selection_changed)
        for model in mc.active_models:
            self.ui.modelSelectorComboBox.addItem(model["title"])

    def refresh(self):
        """
        Refresh everything

        """
        model_result = self._get_selected_model_result(self.presented_forecast)
        self._present_model_result(model_result)

    def _present_model_result(self, model_result):
        """
        Update the forecast results shown in the window with the ISModelResult
        passed in to the function.

        :param model_result: ISModelResult object to display or None to clear
        :type model_result: ISModelResult or None

        """

        self._show_spatial_is(model_result)
        self._show_is_rate(model_result)
        self._show_is_score(model_result)

    def _show_is_rate(self, model_result):
        """
        Update the forecast result labels

        :param model_result: latest model result
        :type model_result: ISModelResult or None

        """
        if model_result is None:
            self.ui.fcTimeLabel.setText('-')
            self.ui.predRateLabel.setText('-')
            self.ui.scoreLabel.setText('-')
        else:
            self.ui.fcTimeLabel.setText(model_result.t_run.ctime())
            rate = '{:.1f}'.format(model_result.cum_result.rate) \
                if not model_result.failed else 'No Results'
            self.ui.predRateLabel.setText(rate)

    def _show_is_score(self, model_result):
        """
        Update the model score labels (time and LL of latest rating)

        :param model_result: model result containing the latest score or None
        :type model_result: ISModelResult or None

        """
        if model_result is None or model_result.cum_result.score is None:
            ll = 'N/A'
            t = ''
        else:
            ll = '{:.1f}'.format(model_result.cum_result.score.LL)
            t = '@ {}'.format(model_result.t_run.ctime())
        self.ui.scoreLabel.setText(ll)
        self.ui.scoreTimeLabel.setText(t)

    def _show_spatial_is(self, model_result):
        """
        Show the latest spatial results (if available) for the model output
        passed into the method.

        :param model_result: model result or None
        :type model_result: ISModelResult or None

        """
        mr = model_result
        if mr is None or mr.failed or not mr.vol_results:
            self.ui.voxelPlot.set_voxel_data(None)
            self.logger.debug('No spatial results available to plot')
        else:
            vol_rates = [r.rate for r in mr.vol_results]
            self.logger.debug('Max voxel rate is {:.1f}'.
                              format(np.amax(vol_rates)))
            self.ui.voxelPlot.set_voxel_data(vol_rates)

    # Helpers

    def _get_selected_model_result(self, fc_result):
        if fc_result is None:
            return None
        is_result = fc_result.is_forecast_result
        if is_result is None:
            return None

        model_idx = self.ui.modelSelectorComboBox.currentIndex()
        model_name = mc.active_models[model_idx]["title"]
        model_result = is_result.model_results.get(model_name)

        return model_result

    # Button Actions

    def action_model_selection_changed(self, _):
        model_result = self._get_selected_model_result(self.presented_forecast)
        self._present_model_result(model_result)