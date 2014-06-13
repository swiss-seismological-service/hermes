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
from isha.common import ModelOutput
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
        self.atls_core.state_changed.connect(self.on_core_state_change)
        self.atls_core.project_loaded.connect(self.on_project_load)
        self.atls_core.forecast_engine.forecast_complete.\
            connect(self.on_forecast_complete)

        if self.atls_core.project is not None:
            self._observe_project_changes(self.atls_core.project)

    # Helpers

    def _observe_project_changes(self, project):
        # Make sure we get updated on project changes
        project.will_close.connect(self.on_project_will_close)
        project.project_time_changed.connect(self.on_project_time_change)
        project.rate_history.history_changed.connect(
            self.on_rate_history_change)

    def _outputs_for_selected_model(self):
        """
        Gets the model outputs for the currently selected model from the core
        and sorts them by t_run.

        :return: List with one or more ModelOutput objects for selected model
                 or None
        :rtype: list[ModelOutput] or None

        """
        idx = self.ui.modelSelectorComboBox.currentIndex()
        model = mc.active_models[idx]
        output_sets = self.atls_core.forecast_engine.output_sets
        if output_sets is None or len(output_sets) == 0:
            mo = None
        else:
            mo = [o.model_outputs.get(model) for o in output_sets.itervalues() \
                  if o.model_outputs.get(model) is not None]
            mo.sort(key=lambda o: o.t_run)
            if len(mo) == 0:
                mo = None
        return mo

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

    def _show_model_outputs(self, model_outputs):
        """
        Update the forecast results shown in the window with the ModelOutputs
        passed in to the function.

        :param model_outputs: List with one or more ModelOutput objects to plot
                              data from or None to clear the display
        :type model_outputs: list[ModelOutput] or None

        """
        if model_outputs is None:
            self._show_forecast_result_history(None)
            self._show_spatial_results(None)
            self._show_latest_model_output(None)
            self._show_latest_model_score(None)
            return

        # Extract latest output
        latest = model_outputs[-1]
        # Extract latest reviewed output
        latest_reviewed = next((o for o in reversed(model_outputs)
                                if o.reviewed), None)

        self._show_forecast_result_history(model_outputs)
        self._show_spatial_results(latest)
        self._show_latest_model_output(latest)
        self._show_latest_model_score(latest_reviewed)


    def _show_latest_model_output(self, model_output):
        """
        Update the forecast result labels

        :param model_output: latest model output
        :type model_output: ModelOutput or None

        """
        if model_output is None:
            self.ui.fc_time_label.setText('-')
            self.ui.pred_rate_label.setText('-')
            self.ui.log_likelihood_label.setText('-')
        else:
            self.ui.fc_time_label.setText(model_output.t_run.ctime())
            rate = '{:.1f}'.format(model_output.result.rate) \
                if model_output.has_results else 'No Results'
            self.ui.pred_rate_label.setText(rate)

    def _show_latest_model_score(self, model_output):
        """
        Update the model score labels (time and LL of latest rating)

        :param model_output: model output containing the latest score or None
        :type model_output: ModelOutput or None

        """
        if model_output is None:
            ll = 'No score available'
            time = ''
        else:
            ll = '{:.1f}'.format(model_output.result.score.LL)
            time = '@ {}'.format(model_output.t_run.ctime())
        self.ui.log_likelihood_label.setText(ll)
        self.ui.rating_time_label.setText(time)

    def _show_forecast_result_history(self, model_outputs):
        """
        Plot the history of forecast result from model_ouputs. If a specific
        model output has no results, a forecast rate of 0 is plotted. If None
        is passed it the plot gets cleared.

        :param model_outputs: list of model outputs or None
        :type model_outputs: list[ModelOutput] or None

        """
        if model_outputs is None:
            self.ui.rate_forecast_plot.set_forecast_data(x=None, y=None)
            return
        epoch = datetime(1970, 1, 1)
        tz = timedelta(seconds=time.timezone)
        x = [(o.t_run - epoch + tz).total_seconds() for o in model_outputs]
        y = [o.result.rate if o.has_results else 0 for o in model_outputs]
        self.logger.debug('Replotting forecasts (' + str(len(x)) + ')')
        self.ui.rate_forecast_plot.set_forecast_data(x, y)

    def _show_spatial_results(self, model_output):
        """
        Show the spatial results (if available) for the model output passed into
        the method.

        :param model_output: model output or None
        :type model_output: ModelOutput or None

        """
        o = model_output
        if o is None or o.has_results is False or o.result.vol_rates is None:
            self.ui.voxel_plot.set_voxel_data(None)
            self.logger.debug('No spatial results available to plot')
        else:
            vol_rates = model_output.result.vol_rates
            self.logger.debug('Max voxel rate is {:.1f}'.\
                              format(np.amax(vol_rates)))
            self.ui.voxel_plot.set_voxel_data(vol_rates)

    def _clear_all(self):
        self._show_model_outputs(None)
        self._show_rates(None)

    # Button Actions

    def action_model_selection_changed(self, index):
        mo = self._outputs_for_selected_model()
        self._show_model_outputs(mo)

    # Handlers for signals from the core

    def on_project_will_close(self, project):
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

    def on_core_state_change(self):
        pass

    def on_project_load(self, project):
        self._observe_project_changes(project)
        self._show_model_outputs(None)
        self._show_rates(project.rate_history)

    def on_forecast_complete(self, result_set):
        mo = self._outputs_for_selected_model()
        self._show_model_outputs(mo)

