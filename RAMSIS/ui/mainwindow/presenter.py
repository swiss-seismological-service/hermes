# Cepyright (C) 2017, ETH Zurich - Swiss Seismological Service SED
"""
Content presentation logic for the main window

Since the main window is fairly complex, we have a dedicated content presenter
that takes care of the ui logic for the main window content (i.e. everything
that is not main menu actions etc.). It mostly coordinates between presenters
for individual window elements.

"""
import datetime
import logging

from PyQt5.QtWidgets import QDialog

from .tabs import GeneralTabPresenter
from .timeline import TimeLinePresenter

from ramsis.datamodel.forecast import Forecast, ForecastScenario
from ramsis.datamodel.forecast import EStage
from RAMSIS.core.controller import LaunchMode
from RAMSIS.core.store import EditingContext
from RAMSIS.ui.base.roles import CustomRoles
from RAMSIS.ui.base.contextaction import (
    ContextAction, ContextActionDelete, Separator)
from RAMSIS.ui.dialog import (
    ForecastConfigDialog, CreateForecastSequenceDialog, ScenarioConfigDialog)
from RAMSIS.ui.mainwindow.viewmodels.forecasttreemodel import (
    ForecastTreeModel)
from RAMSIS.ui.styles import StatusColor


class ContentPresenter(object):
    """
    UI Logic for the main window

    """

    LOGGER = __name__

    def __init__(self, ramsis_core, ui):
        """

        :param ramsis_core: Reference to the core
        :type ramsis_core: RAMSIS.core.controller.Controller
        :param ui: reference to the ui form
        """
        self.logger = logging.getLogger(self.LOGGER)

        self.ramsis_core = ramsis_core
        self.ui = ui

        self.fc_tree_model = None

        def is_lab_mode(_=None):
            return self.ramsis_core.launch_mode == LaunchMode.LAB

        def enable_run(idx):
            # TODO LH: support running individual scenarios
            return (len(idx) == 1 and is_lab_mode() and
                    idx[0].parent().isValid() is False)

        def is_forecast(idx):
            return (len(idx) == 1 and idx[0].parent().isValid() is False)

        # context menu
        self.ui.forecastTreeView.context_actions = [
            ContextAction('Run now', self.action_run_now, enabler=enable_run),
            Separator(),
            ContextAction('Edit ...', self.action_edit,
                          enabler=ContextAction.single_only_enabler),
            ContextActionDelete(self.action_delete,
                                parent_widget=self.ui.forecastTreeView,
                                enabler=is_lab_mode),
            Separator(),
            ContextAction('Create Sequence ...', self.action_create_sequence,
                          enabler=is_forecast), ]

        self.current_scenario = None

        # Presenters for the main window components
        tab_classes = [GeneralTabPresenter]
        self.tab_presenters = [Klass(self.ui) for Klass in tab_classes]
        self.time_line_presenter = TimeLinePresenter(self.ui, ramsis_core)

        # Essential signals from the core
        self.ramsis_core.engine.execution_status_update.\
            connect(self.on_execution_status_update)

    # Display update methods for individual window components

    def show_project(self):
        self.fc_tree_model = ForecastTreeModel(self.ramsis_core)
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
        self.current_scenario = self.ramsis_core.store.get_fresh(
            self.current_scenario)
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
        general_tab = next(t for t in self.tab_presenters
                           if isinstance(t, GeneralTabPresenter))
        general_tab.refresh_status(scenario)

    # Context menu actions

    def action_run_now(self, indexes):
        """ Run a forecast on demand """
        forecast = indexes[0].data(CustomRoles.RepresentedItemRole)
        self.ramsis_core.engine.run(datetime.datetime.utcnow(), forecast.id)

    def action_create_sequence(self, indices):
        if indices:
            item = indices[0].data(CustomRoles.RepresentedItemRole)

            if isinstance(item, Forecast):
                item = self.ramsis_core.store.get_fresh(item)
                dlg = CreateForecastSequenceDialog(item)
                dlg.exec_()

                if dlg.result() == QDialog.Accepted:
                    self.logger.debug(
                        f'Create forecast sequence from forecast {item!r} ...')

                    for i in range(1, dlg.data.num_intervals + 1):
                        cloned = item.clone(with_results=False)
                        cloned.starttime = (
                            item.starttime + datetime.timedelta(
                                seconds=dlg.data.interval * i))
                        if not dlg.data.endtime_fixed:
                            cloned.endtime = (
                                item.endtime + datetime.timedelta(
                                    seconds=dlg.data.interval * i))

                        self.ramsis_core.add_forecast(cloned)
                        self.add_forecast(cloned)

            else:
                raise TypeError(f"Invalid type {item!r} (index={indices[0]}).")

    def action_edit(self, indices):
        if indices:
            item = indices[0].data(CustomRoles.RepresentedItemRole)

            # TODO(damb): Only allow editing under certain conditions.
            if isinstance(item, Forecast):
                ctx = EditingContext(self.ramsis_core.store)
                dlg = ForecastConfigDialog(ctx.get(item))
                dlg.exec_()

                if dlg.result() == QDialog.Accepted:
                    ctx.save()

            elif isinstance(item, ForecastScenario):
                ctx = EditingContext(self.ramsis_core.store)
                scenario = self.ramsis_core.store.get_fresh(ctx.get(item))
                dlg = ScenarioConfigDialog(
                    scenario,
                    self.ramsis_core.store,
                    deserializer_args={
                        'ramsis_proj':
                        self.ramsis_core.project.spatialreference,
                        'external_proj':
                        self.ramsis_core.external_proj,
                        'ref_easting':
                        self.ramsis_core.project.referencepoint_x,
                        'ref_northing':
                        self.ramsis_core.project.referencepoint_y,
                        'transform_func_name':
                        'pyproj_transform_to_local_coords'})
                dlg.exec_()

                if dlg.result() == QDialog.Accepted:
                    merge_items = dlg.updated_items()
                    for mitem in merge_items:
                        ctx.add(mitem)
                        _ = self.ramsis_core.store.get_fresh(mitem)
                    ctx.save()
                    self.current_scenario = self.ramsis_core.store.get_fresh(
                        ctx.get(item))
                    self._refresh_scenario_status()

            else:
                raise TypeError(f"Invalid type {item!r} (index={indices[0]}).")

    def action_delete(self, indexes):
        # TODO LH: this will probably crash with more than one index. We need
        #   to go from the highest to the lowest index and remove child nodes
        #   before parent notes. All this should be taken care of by the base
        #   tree model.
        for idx in indexes:

            item = idx.data(CustomRoles.RepresentedItemRole)
            item = self.ramsis_core.store.get_fresh(item)
            self.fc_tree_model.remove_node(idx.internalPointer(),
                                           self.ramsis_core.project)
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
        if (self.current_scenario and
                self.current_scenario in
                self.ramsis_core.store.session()):
            self.ramsis_core.store.session.expunge(self.current_scenario)
        if idx.parent().isValid():
            scenario = idx.data(role=CustomRoles.RepresentedItemRole)
        else:
            forecast = idx.data(role=CustomRoles.RepresentedItemRole)
            forecast = self.ramsis_core.store.get_fresh(forecast)
            scenario = forecast.scenarios[0] if forecast.scenarios else None
        self.current_scenario = scenario
        if self.current_scenario:
            self.current_scenario = self.ramsis_core.\
                store.get_fresh(self.current_scenario)
        if self.current_scenario:
            self.ramsis_core.store.add(self.current_scenario)
        for tab_presenter in self.tab_presenters:
            self.current_scenario = self.ramsis_core.store.get_fresh(
                self.current_scenario)
            tab_presenter.present_scenario(self.current_scenario)
        self._refresh_scenario_status()

    # Signals from the core
    def on_execution_status_update(self, status):
        general_tab = next(t for t in self.tab_presenters
                           if isinstance(t, GeneralTabPresenter))
        self.current_scenario = self.ramsis_core.store.\
            get_fresh(self.current_scenario)
        if self.current_scenario:
            for run in self.current_scenario[EStage.SEISMICITY].runs:
                self.ramsis_core.store.session.add(run)
            self.ramsis_core.store.add(self.current_scenario)
        general_tab.refresh_status(self.current_scenario)
        self._refresh_scenario_status()
        if self.current_scenario:
            self.ramsis_core.store.session.expunge(self.current_scenario)
