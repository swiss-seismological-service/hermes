# -*- encoding: utf-8 -*-
"""
Controller class for the forecast window
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import logging
from datetime import datetime, timedelta
import time
import ishamodelcontrol as mc
from PyQt4 import QtGui
from views.ui_forecastwindow import Ui_ForecastWindow
from domainmodel.isforecastresult import ISModelResult
from eqstats import SeismicRateHistory
import numpy as np

from ui.views.plots import DisplayRange


class ForecastWindow(QtGui.QDialog):

    def __init__(self, atls_core, **kwargs):
        QtGui.QDialog.__init__(self, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.atls_core = atls_core

        # Some state variables
        self.displayed_project_time = datetime.now()

        # Setup the user interface
        self.ui = Ui_ForecastWindow()
        self.ui.setupUi(self)
        self.ui.rate_forecast_plot.zoom(display_range=2*DisplayRange.DAY)
        # Populate the models chooser combo box
        self.ui.modelSelectorComboBox.currentIndexChanged.connect(
            self.action_model_selection_changed)
        for model in mc.active_models:
            self.ui.modelSelectorComboBox.addItem(model.title)

        # Connect essential signals
        self.atls_core.engine.state_changed.\
            connect(self.on_engine_state_change)
        self.atls_core.project_loaded.connect(self.on_project_load)

        if self.atls_core.project is not None:
            self._observe_project_changes(self.atls_core.project)

    # Helpers

    def _observe_project_changes(self, project):
        # Make sure we get updated on project changes
        project.will_close.connect(self.on_project_will_close)
        project.project_time_changed.connect(self.on_project_time_change)
        project.is_forecast_history.history_changed.connect(
            self.on_forecast_history_change)
        project.rate_history.history_changed.connect(
            self.on_rate_history_change)

    def _results_for_selected_model(self):
        """
        Gets the model results for the currently selected model from the
        project and sorts them by t_run.

        :return: List with one or more ISModelResult objects for selected model
                 or None
        :rtype: list[ISModelResult] or None

        """
        if self.atls_core.project is None:
            return
        idx = self.ui.modelSelectorComboBox.currentIndex()
        model_name = mc.active_models[idx].title
        forecast_history = self.atls_core.project.is_forecast_history
        if len(forecast_history) == 0:
            mr = None
        else:
            mr = [r.model_results.get(model_name) for r in forecast_history]
            mr.sort(key=lambda x: x.t_run)
            if len(mr) == 0:
                mr = None
        return mr

    # Rate display update methods for individual window components with
    # increasing granularity (i.e. top level methods at the top)

    def _show_rates(self, history):
        """
        Replots the seismic rates

        :param history: Rate history object or None
        :type history: SeismicRateHistory or None

        """
        if history is None:
            self.ui.rate_forecast_plot.rate_plot.setData()
            return
        epoch = datetime(1970, 1, 1)
        tz = timedelta(seconds=time.timezone)
        data = [((r.t - epoch + tz).total_seconds(), r.rate)
                for r in history.rates]
        if len(data) == 0:
            return
        x, y = map(list, zip(*data))
        self.ui.rate_forecast_plot.rate_plot.setData(x, y)

    # Forecast result display update methods for individual window components
    # with increasing granularity (i.e. top level methods at the top)

    def _show_model_results(self, model_results):
        """
        Update the forecast results shown in the window with the ISModelResults
        passed in to the function.

        :param model_results: List with one or more ISModelResult objects to
                              plot data from or None to clear the display
        :type model_results: list[ISModelResult] or None

        """
        if model_results is None:
            self._show_forecast_result_history(None)
            self._show_spatial_results(None)
            self._show_latest_model_result(None)
            self._show_latest_model_score(None)
            return

        # Extract latest output
        latest = model_results[-1]
        # Extract latest reviewed output
        latest_reviewed = next((o for o in reversed(model_results)
                                if o.reviewed), None)

        self._show_forecast_result_history(model_results)
        self._show_spatial_results(latest)
        self._show_latest_model_result(latest)
        self._show_latest_model_score(latest_reviewed)

    def _show_latest_model_result(self, model_results):
        """
        Update the forecast result labels

        :param model_results: latest model result
        :type model_results: ISModelResult or None

        """
        if model_results is None:
            self.ui.fc_time_label.setText('-')
            self.ui.pred_rate_label.setText('-')
            self.ui.log_likelihood_label.setText('-')
        else:
            self.ui.fc_time_label.setText(model_results.t_run.ctime())
            rate = '{:.1f}'.format(model_results.cum_result.rate) \
                if not model_results.failed else 'No Results'
            self.ui.pred_rate_label.setText(rate)

    def _show_latest_model_score(self, model_result):
        """
        Update the model score labels (time and LL of latest rating)

        :param model_result: model result containing the latest score or None
        :type model_result: ISModelResult or None

        """
        if model_result is None:
            ll = 'No score available'
            t = ''
        else:
            ll = '{:.1f}'.format(model_result.cum_result.score.LL)
            t = '@ {}'.format(model_result.t_run.ctime())
        self.ui.log_likelihood_label.setText(ll)
        self.ui.rating_time_label.setText(t)

    def _show_forecast_result_history(self, model_results):
        """
        Plot the history of forecast result from model_results. If a specific
        model output has no results, a forecast rate of 0 is plotted. If None
        is passed it the plot gets cleared.

        :param model_results: list of model outputs or None
        :type model_results: list[ISModelResult] or None

        """
        if model_results is None:
            self.ui.rate_forecast_plot.set_forecast_data(x=None, y=None)
            return
        epoch = datetime(1970, 1, 1)
        tz = timedelta(seconds=time.timezone)
        x = [(r.t_run - epoch + tz).total_seconds() for r in model_results]
        y = [r.cum_result.rate if not r.failed else 0 for r in model_results]
        self.logger.debug('Replotting forecasts (' + str(len(x)) + ')')
        self.ui.rate_forecast_plot.set_forecast_data(x, y)

    def _show_spatial_results(self, model_result):
        """
        Show the latest spatial results (if available) for the model output
        passed into the method.

        :param model_result: model result or None
        :type model_result: ISModelResult or None

        """
        mr = model_result
        if mr is None or mr.failed or not mr.vol_results:
            self.ui.voxel_plot.set_voxel_data(None)
            self.logger.debug('No spatial results available to plot')
        else:
            vol_rates = [r.rate for r in mr.vol_results]
            self.logger.debug('Max voxel rate is {:.1f}'.
                              format(np.amax(vol_rates)))
            self.ui.voxel_plot.set_voxel_data(vol_rates)

    def _clear_all(self):
        self._show_model_outputs(None)
        self._show_rates(None)

    # Button Actions

    def action_model_selection_changed(self, _):
        r = self._results_for_selected_model()
        self._show_model_results(r)

    # Handlers for signals from the core

    def on_project_will_close(self, _):
        self._clear_all()

    def on_project_time_change(self, t):
        dt = (t - self.displayed_project_time).total_seconds()
        self.displayed_project_time = t

        # we do a more efficient relative change if the t step is not too big
        if abs(dt) > self.ui.rate_forecast_plot.display_range:
            epoch = datetime(1970, 1, 1)
            pos = (t - epoch).total_seconds() + time.timezone
            self.ui.rate_forecast_plot.marker_pos = pos
            self.ui.rate_forecast_plot.zoom_to_marker()
        else:
            self.ui.rate_forecast_plot.advance_time(dt)

    def on_rate_history_change(self, history):
        self._show_rates(history)

    def on_engine_state_change(self):
        pass

    def on_project_load(self, project):
        self._observe_project_changes(project)
        self._show_model_results(None)
        self._show_rates(project.rate_history)

    def on_forecast_history_change(self, _):
        r = self._results_for_selected_model()
        self._show_model_results(r)
