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
from ramsisdata.forecast import Forecast, Scenario
from tabs import ModelTabPresenter, HazardTabPresenter, RiskTabPresenter, \
    GeneralTabPresenter, SettingsTabPresenter
from timeline import TimeLinePresenter
from ui.mainwindow.viewmodels.forecasttreemodel import ForecastTreeModel, \
    ForecastNode
from ui.styles import STATUS_COLOR_OTHER, STATUS_COLOR_ERROR, \
    STATUS_COLOR_PENDING, STATUS_COLOR_RUNNING, STATUS_COLOR_COMPLETE
from PyQt4.QtGui import QMenu, QAction
from PyQt4.QtCore import Qt


class ContentPresenter(object):
    """
    UI Logic for main window
    
    :param Controller ramsis_core: Ramsis core
    """

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
        self.current_scenario = None

        # Presenters for the main window components
        tab_classes = [ModelTabPresenter, HazardTabPresenter, RiskTabPresenter,
                       GeneralTabPresenter, SettingsTabPresenter]
        self.tab_presenters = [Klass(self.ui) for Klass in tab_classes]
        self.time_line_presenter = TimeLinePresenter(self.ui, ramsis_core)

        # Essential signals from the core
        self.ramsis_core.engine.job_status_update.\
            connect(self.on_job_status_update)

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
            tab_presenter.present_scenario(None)

    def _refresh_scenario_status(self):
        """
        Show the overall status of the currently selected forecast

        """
        scenario = self.current_scenario
        if scenario is None:
            msg = 'No scenario selected'
            color = STATUS_COLOR_OTHER
            errors = False
        else:
            errors = scenario.has_errors()
            status = scenario.summary_status
            fc = scenario.forecast_input.forecast
            dt = fc.forecast_time - self.ramsis_core.project.project_time
            if status == Scenario.PENDING:
                h = int(dt.total_seconds() / 3600)
                m = int((dt.total_seconds() % 3600) / 60)
                if dt.total_seconds > 0:
                    pre = 'Scenario scheduled to run in '
                    color = STATUS_COLOR_PENDING
                else:
                    pre = 'Scenario overdue for '
                    color = STATUS_COLOR_OTHER
                if h > 24:
                    msg = pre + '{} days'.format(h / 24)
                elif h > 0:
                    msg = pre + '{} hours {} minutes'.format(h, m)
                else:
                    msg = pre + '{} minutes'.format(m)
            elif status == Scenario.RUNNING:
                color = STATUS_COLOR_RUNNING
                msg = 'Scenario is currently being computed'
            elif status == Scenario.COMPLETE:
                color = STATUS_COLOR_COMPLETE
                msg = 'Scenario computation complete'
            else:
                color = STATUS_COLOR_OTHER
                msg = 'Scenario computation partially complete'

        if errors:
            msg += ' (with errors)'
            color = STATUS_COLOR_ERROR
        text_color = 'black' if color == STATUS_COLOR_OTHER else 'white'
        self.ui.fcStatusLabel.setText(msg)
        self.ui.statusAreaWidget.setStyleSheet('background-color: {};'
                                               'color: {};'
                                               .format(color, text_color))

    # Context menu actions

    def action_run_now(self, checked):
        self.ramsis_core.engine.run(datetime.utcnow(), self.run_action.data())

    # Handlers for signals from the UI

    def on_project_will_close(self, _):
        self._clear_all()
        fc_selection = self.ui.forecastTreeView.selectionModel()
        fc_selection.selectionChanged.disconnect(self.on_fc_selection_change)
        self.ui.forecastTreeView.setModel(None)
        self.fc_tree_model = None

    def on_project_time_change(self, t):
        pass

    def on_forecasts_change(self, _):
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
            self.current_scenario = forecast.input.scenarios[scenario_idx]
        except IndexError:
            self.current_scenario = None
        for tab_presenter in self.tab_presenters:
            tab_presenter.present_scenario(self.current_scenario)
        self._refresh_scenario_status()

    def on_context_menu_requested(self, pos):
        if self.fc_tree_model is None:
            return
        idx = self.ui.forecastTreeView.indexAt(pos)
        node = idx.internalPointer()
        if isinstance(node, ForecastNode):
            forecast = node.item
            self.run_action.setData(forecast)
            self.context_menu.exec_(self.ui.forecastTreeView.mapToGlobal(pos))

    # Signals from the core

    def on_job_status_update(self, status):
        general_tab = next(t for t in self.tab_presenters
                           if isinstance(t, GeneralTabPresenter))
        general_tab.refresh_status()
        self._refresh_scenario_status()
