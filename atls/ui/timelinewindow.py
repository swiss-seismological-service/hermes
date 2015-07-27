# -*- encoding: utf-8 -*-
"""
Controller class for the timeline window

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import os
import logging
import time
from datetime import datetime, timedelta
from PyQt4 import QtGui, uic
import core.ismodelcontrol as mc
from ui.views.plots import DisplayRange

ui_path = os.path.dirname(__file__)
TIMELINE_WINDOW_PATH = os.path.join(ui_path, 'views', 'timelinewindow.ui')
Ui_TimelineWindow = uic.loadUiType(TIMELINE_WINDOW_PATH)[0]


class TimelinePresenter(object):

    def __init__(self, ui, time_plot_widget):
        self.ui = ui
        self._history = None
        self.time_plot_widget = time_plot_widget
        self.displayed_project_time = datetime.now()
        self.logger = logging.getLogger(__name__)

    @property
    def history(self):
        return self._history

    @history.setter
    def history(self, history):
        if self.history is not None:
            self.history.history_changed.disconnect(self._on_history_changed)
        self._history = history
        if history is not None:
            self._history.history_changed.connect(self._on_history_changed)
        self.replot()

    def show_current_time(self, t):
        dt = (t - self.displayed_project_time).total_seconds()
        self.displayed_project_time = t
        # we do a more efficient relative change if the change is not too big
        if abs(dt) > self.ui.seismic_data_plot.display_range:
            epoch = datetime(1970, 1, 1)
            pos = (t - epoch).total_seconds()
            self.time_plot_widget.marker_pos = pos
        else:
            self.time_plot_widget.advance_time(dt)

    def zoom(self, display_range):
        self.time_plot_widget.zoom(display_range=display_range)

    def replot(self, max_time=None):
        raise NotImplementedError('Must be implemented by children')

    def _on_history_changed(self, change):
        self.replot()


class SeismicityPresenter(TimelinePresenter):

    def _on_history_changed(self, change):
        t = change.get('simulation_time')
        if t is None:
            self.replot()
        else:
            self.replot(max_time=t)

    def replot(self, max_time=None):
        """
        Plot the data in the seismic catalog

        :param max_time: if not None, plot catalog up to max_time only

        """
        epoch = datetime(1970, 1, 1)
        events = self.history.all_events()
        if max_time:
            data = [((e.date_time - epoch).total_seconds(), e.magnitude)
                    for e in events if e.date_time < max_time]
        else:
            data = [((e.date_time - epoch).total_seconds(), e.magnitude)
                    for e in events]
        self.time_plot_widget.plot.setData(pos=data)


class HydraulicsPresenter(TimelinePresenter):

    def _on_history_changed(self, change):
        t = change.get('simulation_time')
        if t is None:
            self.replot()
        else:
            self.replot(max_time=t)

    def replot(self, max_time=None):
        """
        Plot the data in the hydraulic catalog

        :param max_time: if not None, plot catalog up to max_time only

        """
        epoch = datetime(1970, 1, 1)
        events = self.history.all_events()
        if max_time is None:
            max_time = datetime.max

        data = [((e.date_time - epoch).total_seconds(), e.flow_xt)
                for e in events if e.date_time < max_time]

        x, y = map(list, zip(*data)) if len(data) > 0 else ([], [])
        self.time_plot_widget.plot.setData(x, y)


class ForecastsPresenter(TimelinePresenter):
    """
    Presents the forecasts timeline (rates and forecasted rates)

    """

    def __init__(self, ui, plot):
        super(ForecastsPresenter, self).__init__(ui, plot)
        # The forecast plot shows two histories: forecast and actual rates
        self._rate_history = None
        # Populate the models chooser combo box
        self.ui.isModelComboBox.clear()
        for model in mc.active_models:
            self.ui.isModelComboBox.addItem(model.title)
        self.ui.isModelComboBox.currentIndexChanged.connect(
            self.action_model_selection_changed)

    @property
    def rate_history(self):
        return self._rate_history

    @rate_history.setter
    def rate_history(self, rate_history):
        if self.rate_history is not None:
            self.rate_history.history_changed.\
                disconnect(self.on_rate_history_change)
        self._rate_history = rate_history
        if self.rate_history is not None:
            self.rate_history.history_changed.\
                connect(self._on_history_changed)
        self.replot()

    def replot(self, max_time=None):
        self._show_rates()
        self._show_forecast_rates()

    # Model result extraction

    def _results_for_selected_model(self):
        """
        Gets the model results for the currently selected model from the
        project and sorts them by t_run.

        :return: List with one or more ISModelResult objects for selected model
                 or None
        :rtype: list[ISModelResult] or None

        """
        if self.history is None:
            return
        idx = self.ui.isModelComboBox.currentIndex()
        model_name = mc.active_models[idx].title
        is_forecasts = [fcr.is_forecast_result for fcr in self.history
                        if fcr.is_forecast_result is not None]
        if len(is_forecasts) == 0:
            mr = None
        else:
            mr = [r.model_results.get(model_name) for r in is_forecasts]
            mr.sort(key=lambda x: x.t_run)
            if len(mr) == 0:
                mr = None
        return mr

    # Signals we observe

    def on_rate_history_change(self, _):
        self._show_rates()

    def on_forecast_history_change(self, _):
        self._show_forecast_rates()

    # Rate display update methods

    def _show_rates(self):
        """
        Replots the past seismic rates

        """
        if self.rate_history is None:
            self.time_plot_widget.rate_plot.setData()
            return
        epoch = datetime(1970, 1, 1)
        tz = timedelta(seconds=time.timezone)
        data = [((r.t - epoch + tz).total_seconds(), r.rate)
                for r in self.rate_history.rates]
        if len(data) == 0:
            return
        x, y = map(list, zip(*data))
        self.time_plot_widget.rate_plot.setData(x, y)

    # Forecast result display update methods

    def _show_forecast_rates(self):
        """
        Update the forecast results shown in the window with the ISModelResults
        passed in to the function.

        """
        model_results = self._results_for_selected_model()
        if model_results is None:
            self.time_plot_widget.set_forecast_data(x=None, y=None)
            return
        epoch = datetime(1970, 1, 1)
        tz = timedelta(seconds=time.timezone)
        x = [(r.t_run - epoch + tz).total_seconds() for r in model_results]
        y = [r.cum_result.rate if not r.failed else 0 for r in model_results]
        self.logger.debug('Replotting forecasts (' + str(len(x)) + ')')
        self.time_plot_widget.set_forecast_data(x, y)

    # Button Actions

    def action_model_selection_changed(self, _):
        self._show_forecast_rates()


class TimelineWindow(QtGui.QDialog):

    def __init__(self, atls_core, **kwargs):
        QtGui.QMainWindow.__init__(self, **kwargs)
        self.logger = logging.getLogger(__name__)

        # References
        self.atls_core = atls_core
        self.project = None

        # Setup the user interface
        self.ui = Ui_TimelineWindow()
        self.ui.setupUi(self)

        # Setup presenters for subviews
        self.hydraulics_presenter = \
            HydraulicsPresenter(self.ui, self.ui.hydraulic_data_plot)
        self.seismicity_presenter = \
            SeismicityPresenter(self.ui, self.ui.seismic_data_plot)
        self.forecasts_presenter = \
            ForecastsPresenter(self.ui, self.ui.forecasts_data_plot)

        # Link the x axis of the seismicity view with the x axis of the
        # hydraulics view
        h_view = self.ui.hydraulic_data_plot.plotItem.getViewBox()
        s_view = self.ui.seismic_data_plot.plotItem.getViewBox()
        h_view.setXLink(s_view)

        # Hook up essentials signals from the core
        self.atls_core.project_loaded.connect(self.on_project_load)

        if self.atls_core.project is not None:
            self.on_project_load(self.atls_core.project)

    # Observed signals from the core

    def on_project_load(self, project):
        """
        :param project: AtlsProject
        """
        self.project = project

        # Make sure we get updated on project changes
        project.will_close.connect(self.on_project_will_close)
        project.project_time_changed.connect(self.on_project_time_change)

        # Update all plots and our status
        self._present_project(project)
        self.seismicity_presenter.zoom(DisplayRange.WEEK)
        self.forecasts_presenter.zoom(DisplayRange.WEEK)
        # Trigger a project time change manually, so the plots will update
        self.on_project_time_change(project.project_time)

    def on_project_will_close(self, project):
        project.will_close.disconnect(self.on_project_will_close)
        project.project_time_changed.disconnect(self.on_project_time_change)
        self.project = None
        self._present_project(None)

    def on_project_time_change(self, t):
        for p in (self.seismicity_presenter, self.hydraulics_presenter,
                  self.forecasts_presenter):
            p.show_current_time(t)
        # We need to do this on only one since the plots are linked
        self.seismicity_presenter.time_plot_widget.zoom_to_marker()
        self.forecasts_presenter.time_plot_widget.zoom_to_marker()

    def _present_project(self, project):
        if project is None:
            self.hydraulics_presenter.history = None
            self.seismicity_presenter.history = None
            self.forecasts_presenter.history = None
            self.forecasts_presenter.rate_history = None
        else:
            self.hydraulics_presenter.history = project.hydraulic_history
            self.seismicity_presenter.history = project.seismic_history
            self.forecasts_presenter.history = project.forecast_history
            self.forecasts_presenter.rate_history = project.rate_history
