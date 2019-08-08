# Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED
"""
Content presentation logic for the main window

Since the main window is fairly complex, we have a dedicated content presenter
that takes care of the ui logic for the main window content (i.e. everything
that is not main menu actions etc.). It mostly coordinates between presenters
for individual window elements.

"""
from datetime import datetime

from .tabs import ModelTabPresenter, HazardTabPresenter, \
    GeneralTabPresenter
from .timeline import TimeLinePresenter

from ramsis.datamodel.forecast import Forecast, ForecastScenario

from RAMSIS.core.controller import LaunchMode
from RAMSIS.ui.base.roles import CustomRoles
from RAMSIS.ui.base.contextaction import (
    ContextAction, ContextActionDelete, Separator)
from RAMSIS.ui.dialog import ForecastConfigDialog
from RAMSIS.ui.mainwindow.viewmodels.forecasttreemodel import (
    ForecastTreeModel, ForecastNode)
from RAMSIS.ui.styles import StatusColor


class ContentPresenter(object):
    """
    UI Logic for the main window

    """

    def __init__(self, ramsis_core, ui):
        """

        :param ramsis_core: Reference to the core
        :type ramsis_core: RAMSIS.core.controller.Controller
        :param ui: reference to the ui form
        """
        self.ramsis_core = ramsis_core
        self.ui = ui

        self.fc_tree_model = None

        def is_lab_mode(_=None):
            return self.ramsis_core.launch_mode == LaunchMode.LAB

        def enable_run(idx):
            # TODO LH: support running individual scenarios
            return (len(idx) == 1 and is_lab_mode() and
                    idx[0].parent().isValid() is False)

        # context menu
        self.ui.forecastTreeView.context_actions = [
            ContextAction('Run now', self.action_run_now, enabler=enable_run),
            Separator(),
            ContextAction('Edit ...', self.action_edit),
            ContextActionDelete(self.action_delete,
                                parent_widget=self.ui.forecastTreeView,
                                enabler=is_lab_mode)]
        self.current_scenario = None

        # Presenters for the main window components
        tab_classes = [ModelTabPresenter, HazardTabPresenter,
                       GeneralTabPresenter]
        self.tab_presenters = [Klass(self.ui) for Klass in tab_classes]
        self.time_line_presenter = TimeLinePresenter(self.ui, ramsis_core)

        # Essential signals from the core
        self.ramsis_core.engine.execution_status_update.\
            connect(self.on_execution_status_update)

    # Display update methods for individual window components

    def show_project(self):
        project = self.ramsis_core.project
        self.fc_tree_model = ForecastTreeModel(project)
        self.ui.forecastTreeView.setModel(self.fc_tree_model)
        # observe selection changes
        fc_selection = self.ui.forecastTreeView.selectionModel()
        fc_selection.selectionChanged.connect(self.on_fc_selection_change)

    def add_forecast(self, forecast):
        self.fc_tree_model.add_forecast(forecast)

    def clear_project(self):
        self._clear_all()

    def _clear_all(self):
        for tab_presenter in self.tab_presenters:
            tab_presenter.present_scenario(None)

    def _refresh_scenario_status(self):
        """
        Show the overall status of the currently selected forecast

        """
        color = StatusColor.OTHER
        errors = False
        msg = ''

        scenario = self.current_scenario
        if scenario is None:
            msg = 'No scenario selected'
        else:
            # TODO LH: adapt to new model
            pass
            # errors = scenario.has_errors()
            # status = scenario.summary_status
            # fc = scenario.forecast_input.forecast
            # dt = fc.forecast_time - self.ramsis_core.project.project_time
            # if status == ForecastScenario.PENDING:
            #     h = int(dt.total_seconds() / 3600)
            #     m = int((dt.total_seconds() % 3600) / 60)
            #     if dt.total_seconds() > 0:
            #         pre = 'Scenario scheduled to run in '
            #         color = StatusColor.PENDING
            #     else:
            #         pre = 'Scenario overdue for '
            #         color = StatusColor.OTHER
            #     if h > 24:
            #         msg = pre + '{} days'.format(h / 24)
            #     elif h > 0:
            #         msg = pre + '{} hours {} minutes'.format(h, m)
            #     else:
            #         msg = pre + '{} minutes'.format(m)
            # elif status == ForecastScenario.RUNNING:
            #     color = StatusColor.RUNNING
            #     msg = 'Scenario is currently being computed'
            # elif status == ForecastScenario.COMPLETE:
            #     color = StatusColor.COMPLETE
            #     msg = 'Scenario computation complete'
            # else:
            #     color = StatusColor.OTHER
            #     msg = 'Scenario computation partially complete'

        if errors:
            msg += ' (with errors)'
            color = StatusColor.ERROR
        text_color = 'black' if color == StatusColor.OTHER else 'white'
        self.ui.fcStatusLabel.setText(msg)
        self.ui.statusAreaWidget.setStyleSheet('background-color: transparent;'
                                               'color: transparent;'
                                               .format(color, text_color))

    # Context menu actions

    def action_run_now(self, indexes):
        """ Run a forecast on demand """
        forecast = indexes[0].data(CustomRoles.RepresentedItemRole)
        self.ramsis_core.engine.run(datetime.utcnow(), forecast)

    def action_edit(self, indices):
        if indices:
            if len(indices) > 1:
                raise ValueError(
                    'Multiple entities cannot be edited simultaneously.')

            item = indices[0].data(CustomRoles.RepresentedItemRole)

            if isinstance(item, Forecast):
                dlg = ForecastConfigDialog.from_forecast(item)
                dlg.exec_()
                if dlg.data is not None:
                    self.ramsis_core.update_project(item, dlg.data)

            elif isinstance(item, ForecastScenario):
                # TODO(damb): Make scenario editable
                pass

            else:
                raise TypeError(f"Invalid type {item!r} (index={indices[0]}).")

    def action_delete(self, indexes):
        # TODO LH: this will probably crash with more than one index. We need
        #   to go from the highest to the lowest index and remove child nodes
        #   before parent notes. All this should be taken care of by the base
        #   tree model.
        for idx in indexes:
            item = idx.data(CustomRoles.RepresentedItemRole)
            self.fc_tree_model.remove_node(idx.internalPointer())
            self.ramsis_core.store.delete(item)
        self.ramsis_core.store.save()

    # Handlers for signals from the UI

    def on_project_will_close(self, _):
        self._clear_all()
        fc_selection = self.ui.forecastTreeView.selectionModel()
        fc_selection.selectionChanged.disconnect(self.on_fc_selection_change)
        self.ui.forecastTreeView.setModel(None)
        self.fc_tree_model = None

    def on_fc_selection_change(self, selection):
        idx = selection.indexes()[0]

        if idx.parent().isValid():
            scenario = idx.data(role=CustomRoles.RepresentedItemRole)
        else:
            forecast = idx.data(role=CustomRoles.RepresentedItemRole)
            scenario = forecast.scenarios[0] if forecast.scenarios else None
        self.current_scenario = scenario
        for tab_presenter in self.tab_presenters:
            tab_presenter.present_scenario(self.current_scenario)
        self._refresh_scenario_status()

    # Signals from the core

    def on_execution_status_update(self, _):
        general_tab = next(t for t in self.tab_presenters
                           if isinstance(t, GeneralTabPresenter))
        general_tab.refresh_status()
        self._refresh_scenario_status()
