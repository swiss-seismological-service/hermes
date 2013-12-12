# -*- encoding: utf-8 -*-
"""
Controller class for the forecast window
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import logging
from datetime import datetime

from PyQt4 import QtGui
from views.ui_forecastwindow import Ui_ForecastWindow

from ui.views.plots import DisplayRange


class ForecastWindow(QtGui.QDialog):

    def __init__(self, atlas_core, **kwargs):
        QtGui.QDialog.__init__(self, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.atlas_core = atlas_core

        # Some state variables
        self.displayed_project_time = datetime.now()
        self.current_result_set = {}

        # Setup the user interface
        self.ui = Ui_ForecastWindow()
        self.ui.setupUi(self)
        self.ui.rate_forecast_plot.zoom(display_range=2*DisplayRange.DAY)
        # Populate the models chooser combo box
        self.ui.modelSelectorComboBox.currentIndexChanged.connect(
            self.on_model_selection_changed)
        for model in self.atlas_core.forecast_engine.models:
            self.ui.modelSelectorComboBox.addItem(model.title)

        # Connect essential signals
        self.atlas_core.state_changed.connect(self.on_core_state_change)
        self.atlas_core.project_loaded.connect(self.on_project_load)
        self.atlas_core.forecast_engine.forecast_complete.\
            connect(self.on_forecast_complete)

        if self.atlas_core.project is not None:
            self.connect_project(self.atlas_core.project)

    def connect_project(self, project):
        # Make sure we get updated on project changes
        project.will_close.connect(self.on_project_will_close)
        project.project_time_changed.connect(self.on_project_time_change)
        project.rate_history.history_changed.connect(
            self.on_rate_history_change)

    def replot_seismic_rates(self, history):
        """
        Replots the forecasted and actual seismic _rates

        """
        epoch = datetime(1970, 1, 1)
        data = [((r.t - epoch).total_seconds(), r.rate) for r in history.rates]
        if len(data) == 0:
            return

        x, y = map(list, zip(*data))
        self.ui.rate_forecast_plot.rate_plot.setData(x, y)

    def replot_forecasts(self):
        idx = self.ui.modelSelectorComboBox.currentIndex()
        model = self.atlas_core.forecast_engine.models[idx]
        results = self.current_result_set.get(model)

        if results is None or len(results.t_results) == 0:
            self.clear_forecasts()
        else:
            epoch = datetime(1970, 1, 1)
            x = [(t - epoch).total_seconds() for t in results.t_results]
            y = results.rates

            self.logger.info('replotting forecasts (' + str(len(x))) + ')'
            self.ui.rate_forecast_plot.set_forecast_data(x, y)

    # Plot helpers

    def clear_forecasts(self):
        self.current_result_set = {}
        self.ui.rate_forecast_plot.set_forecast_data(x=None, y=None)

    def clear_rates(self):
        self.ui.rate_forecast_plot.rate_plot.setData()

    def clear_plots(self):
        self.clear_forecasts()
        self.clear_rates()

    # Signal slots

    def on_model_selection_changed(self, index):
        self.replot_forecasts()

    def on_project_will_close(self, project):
        self.clear_plots()

    def on_project_time_change(self, time):
        dt = (time - self.displayed_project_time).total_seconds()
        self.displayed_project_time = time

        # we do a more efficient relative change if the time step is not too big
        if abs(dt) > self.ui.rate_forecast_plot.display_range:
            epoch = datetime(1970, 1, 1)
            pos = (time - epoch).total_seconds()
            self.ui.rate_forecast_plot.marker_pos = pos
            self.ui.rate_forecast_plot.zoom_to_marker()
        else:
            self.ui.rate_forecast_plot.advance_time(dt)

    def on_rate_history_change(self, history):
        self.replot_seismic_rates(history)

    def on_core_state_change(self):
        pass

    def on_project_load(self, project):
        self.connect_project(project)
        self.clear_forecasts()
        self.replot_seismic_rates()

    def on_forecast_complete(self, result_set):
        self.current_result_set = result_set
        self.replot_forecasts()