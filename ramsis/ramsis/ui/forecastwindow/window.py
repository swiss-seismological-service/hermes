# -*- encoding: utf-8 -*-
"""
Controller class for the forecasts window

Copyright (C) 2014, ETH Zurich - Swiss Seismological Service SED

"""

import logging
import os
from datetime import datetime
from PyQt4 import QtGui, uic
from tabs import ModelTabPresenter, HazardTabPresenter, RiskTabPresenter, \
    GeneralTabPresenter
from timeline import TimeLinePresenter
from forecasttreemodel import ForecastTreeModel
from ramsisdata.forecast import Forecast
from data import dummy_data


ui_path = os.path.dirname(__file__)
FC_WINDOW_PATH = os.path.join('ramsis', 'ui', 'views', 'forecastswindow.ui')
Ui_ForecastsWindow = uic.loadUiType(FC_WINDOW_PATH)[0]


STATUS_COLOR_PLANNED = '#0099CC'
STATUS_COLOR_COMPLETE = '#00CC99'
STATUS_COLOR_RUNNING = '#FF470A'
STATUS_COLOR_PENDING = '#CC0033'
STATUS_COLOR_OTHER = '#9900CC'

class ForecastsWindow(QtGui.QDialog):

    def __init__(self, ramsis_core, **kwargs):
        QtGui.QDialog.__init__(self, **kwargs)
        self.logger = logging.getLogger(__name__)

        # References
        self.ramsis_core = ramsis_core
        self.fc_tree_model = None

        # Setup the user interface
        self.ui = Ui_ForecastsWindow()
        self.ui.setupUi(self)

        # Presenters for the main window components
        tab_classes = [ModelTabPresenter, HazardTabPresenter, RiskTabPresenter,
                       GeneralTabPresenter]
        self.tab_presenters = [Klass(self.ui) for Klass in tab_classes]
        self.time_line_presenter = TimeLinePresenter(self.ui, ramsis_core)

        # Connect essential signals
        # ... from the core
        self.ramsis_core.project_loaded.connect(self.on_project_load)

        # for testing only
        #if self.ramsis_core.project is not None:
        #    self._load_project_data(self.ramsis_core.project)
        self._load_project_data(dummy_data())

    # Helpers

    def _load_project_data(self, project):
        self._observe_project_changes(project)

        # setup view model

        def date_display(x):
            return x.t_run.ctime()

        # roles = {
        #     Qt.DisplayRole: date_display
        # }
        self.fc_tree_model = ForecastTreeModel(project.forecast_set)
        self.ui.forecastTreeView.setModel(self.fc_tree_model)

        # observe selection changes

        fc_selection = self.ui.forecastTreeView.selectionModel()
        fc_selection.selectionChanged.connect(self.on_fc_selection_change)

    def _observe_project_changes(self, project):
        # Make sure we get updated on project changes
        project.will_close.connect(self.on_project_will_close)
        project.project_time_changed.connect(self.on_project_time_change)

    # Display update methods for individual window components with
    # increasing granularity (i.e. top level methods at the top)

    def _refresh_forecast_list(self):
        """
        Refresh the list of forecasts

        """
        self.fc_tree_model.refresh()

    def _clear_all(self):
        for tab_presenter in self.tab_presenters:
            tab_presenter.present_forecast_result(None)

    def _refresh_fc_status(self, fc):
        """
        Show the overall status of the currently selected forecast

        :param Forecast fc: currently selected forecast

        """
        # FIXME: base this on fc.status once we have that
        dt = fc.forecast_time - self.ramsis_core.project.project_time
        if dt.total_seconds() > 0:
            color = STATUS_COLOR_PLANNED
            h = int(dt.total_seconds() / 3600)
            m = int((dt.total_seconds() % 3600) / 60)
            if h > 24:
                msg = 'Forecast due in {} days'.format(h / 24)
            elif h > 0:
                msg = 'Forecast due in {} hours {} minutes'.format(h, m)
            else:
                msg = 'Forecast due in {} minutes'.format(m)
        else:
            # if fc.status == fc.STATUS_COMPLETE:
            color = STATUS_COLOR_COMPLETE
            msg = 'Forecast completed'
            # elif fc.status == fc.STATUS_RUNNING:
            #     color = STATUS_COLOR_RUNNING
            # else:
            #     color = STATUS_COLOR_PENDING
        self.ui.fcStatusLabel.setText(msg)
        self.ui.statusAreaWidget.setStyleSheet('background-color: {};'
                                               .format(color))


    # Handlers for signals from the core

    def on_project_will_close(self, _):
        self._clear_all()
        fc_selection = self.ui.forecastListView.selectionModel()
        fc_selection.selectionChanged.disconnect(self.on_fc_selection_change)
        self.ui.forecastListView.setModel(None)
        self.fc_tree_model = None

    def on_project_time_change(self, t):
        pass

    def on_project_load(self, project):
        """
        :param project: RAMSIS project
        :type project: Project

        """
        self._load_project_data(project)

    # Handlers for signals from the UI

    def on_fc_selection_change(self, selection):
        idx = selection.indexes()[0]
        if idx.parent().isValid():
            forecast_idx = idx.parent().row()
            scenario_idx = idx.row()
        else:
            forecast_idx = idx.row()
            scenario_idx = 0
        try:
            forecast_set = self.fc_tree_model.forecast_set
            forecast = forecast_set.forecasts[forecast_idx]
            scenario = forecast.input.scenarios[scenario_idx]
        except IndexError:
            forecast = None
            scenario = None
        for tab_presenter in self.tab_presenters:
            tab_presenter.present_scenario(scenario)
        self._refresh_fc_status(forecast)
