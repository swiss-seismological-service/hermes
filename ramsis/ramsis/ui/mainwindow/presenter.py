# -*- encoding: utf-8 -*-
"""
Content presentation logic for the main window

Since the main window is fairly complex, we have a dedicated content presenter
that takes care of the ui logic for the main window content (i.e. everything
that is not menu actions etc.). It mostly coordinates between presenters for
individual window elements.

Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED

"""
from datetime import datetime
from ramsisdata.forecast import Forecast
from tabs import ModelTabPresenter, HazardTabPresenter, RiskTabPresenter, \
    GeneralTabPresenter
from timeline import TimeLinePresenter
from ui.mainwindow.viewmodels.forecasttreemodel import ForecastTreeModel, \
    ForecastNode
from PyQt4.QtGui import QMenu, QAction
from PyQt4.QtCore import Qt

STATUS_COLOR_PLANNED = '#0099CC'
STATUS_COLOR_COMPLETE = '#00CC99'
STATUS_COLOR_DISABLED = '#D0D0D0'
STATUS_COLOR_ERROR = '#FF470A'
STATUS_COLOR_RUNNING = '#9900CC'
STATUS_COLOR_OTHER = '#F8E81C'


class ContentPresenter(object):

    def __init__(self, ramsis_core, ui):
        self.ramsis_core = ramsis_core
        self.ui = ui

        self.fc_tree_model = None
        self.context_menu = QMenu(self.ui.forecastTreeView)
        self.run_action = QAction('Run now', self.context_menu)
        self.run_action.triggered.connect(self.action_run_now)
        self.context_menu.addAction(self.run_action)
        self.ui.forecastTreeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.forecastTreeView.customContextMenuRequested.connect(
            self.on_context_menu_requested
        )

        # Presenters for the main window components
        tab_classes = [ModelTabPresenter, HazardTabPresenter, RiskTabPresenter,
                       GeneralTabPresenter]
        self.tab_presenters = [Klass(self.ui) for Klass in tab_classes]
        self.time_line_presenter = TimeLinePresenter(self.ui, ramsis_core)

    # Display update methods for individual window components with
    # increasing granularity (i.e. top level methods at the top)

    def present_current_project(self):
        project = self.ramsis_core.project
        self._observe_project_changes(project)
        self.fc_tree_model = ForecastTreeModel(project.forecast_set)
        self.ui.forecastTreeView.setModel(self.fc_tree_model)
        # observe selection changes
        fc_selection = self.ui.forecastTreeView.selectionModel()
        fc_selection.selectionChanged.connect(self.on_fc_selection_change)

    def _observe_project_changes(self, project):
        # Make sure we get updated on project changes
        project.will_close.connect(self.on_project_will_close)
        project.project_time_changed.connect(self.on_project_time_change)
        project.forecast_set.forecasts_changed.connect(
            self.on_forecasts_change)

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

    # Context menu actions

    def action_run_now(self, checked):
        self.ramsis_core.engine.run(datetime.now(), self.run_action.data())

    # Handlers for signals from the UI

    def on_project_will_close(self, _):
        self._clear_all()
        fc_selection = self.ui.forecastListView.selectionModel()
        fc_selection.selectionChanged.disconnect(self.on_fc_selection_change)
        self.ui.forecastListView.setModel(None)
        self.fc_tree_model = None

    def on_project_time_change(self, t):
        pass

    def on_forecasts_change(self):
        self._refresh_forecast_list()

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

    def on_context_menu_requested(self, pos):
        if self.fc_tree_model is None:
            return
        idx = self.ui.forecastTreeView.indexAt(pos)
        node = idx.internalPointer()
        if isinstance(node, ForecastNode):
            forecast = node.item
            self.run_action.setData(forecast)
            self.context_menu.exec_(self.ui.forecastTreeView.mapToGlobal(pos))
