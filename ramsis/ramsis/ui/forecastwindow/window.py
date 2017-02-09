# -*- encoding: utf-8 -*-
"""
Controller class for the forecasts window

Copyright (C) 2014, ETH Zurich - Swiss Seismological Service SED

"""

import logging
import os
from PyQt4 import QtGui, uic
from tabs import ModelTabPresenter, HazardTabPresenter, RiskTabPresenter
from forecasttreemodel import ForecastTreeModel

from data import dummy_data


ui_path = os.path.dirname(__file__)
FC_WINDOW_PATH = os.path.join('ramsis', 'ui', 'views', 'forecastswindow.ui')
Ui_ForecastsWindow = uic.loadUiType(FC_WINDOW_PATH)[0]


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

        # Presenters for the main window components (the tabs)
        tab_classes = [ModelTabPresenter, HazardTabPresenter, RiskTabPresenter]
        self.tab_presenters = [Klass(self.ui) for Klass in tab_classes]

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
        idx = selection.indexes()
        if len(idx) != 1:
            fc = None
        else:
            fc = self.fc_tree_model.event_history[idx[0].row()]
        for tab_presenter in self.tab_presenters:
            tab_presenter.present_forecast_result(fc)
