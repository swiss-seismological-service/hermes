# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
UI to create, edit and load projects.

"""
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import QWidget
from RAMSIS.core.builder import default_project
from RAMSIS.ui.base.roles import CustomRoles
from RAMSIS.ui.base.state import UiStateMachine
from RAMSIS.ui.utils import UiForm
from RAMSIS.ui.viewmodels.projectstablemodel import ProjectsTableModel
from RAMSIS.ui.settingswindow import ProjectSettingsWindow


class ProjectManagementWindow(QWidget, UiForm('projectmanagementwindow.ui')):
    """
    UI to create, edit and load projects.

    """
    def __init__(self, app, *args, **kwargs):
        """
        ProjectManagementWindow initializer

        :param core: Reference to the RAMSIS application core
        :type core: RAMSIS.core.controller.Controller

        """
        super().__init__(*args, **kwargs)
        self.app = app
        self.setWindowModality(Qt.ApplicationModal)

        # Setup the ui state machine
        create = self.ui.createProjectButton
        open = self.ui.openProjectButton
        title = self.ui.titleLabel
        self._ui_state_machine = UiStateMachine(initial='no_data')
        self._ui_state_machine.add_states([
            {'name': 'no_data',
             'ui_disable': [create, open],
             'ui_enable': {'on_exit': create},
             'ui_text': {'on_enter': {title: 'No database connected'},
                         'on_exit': {title: 'Projects'}}},
            {'name': 'nothing_selected', 'ui_disable': open},
            {'name': 'current_selected', 'ui_disable': open},
            {'name': 'other_selected', 'ui_enable': open}
        ])

        # Populate data
        if app.ramsis_core.store:
            self._load_projects()
            self._ui_state_machine.to_nothing_selected()

    # UI signals

    @pyqtSlot(name='on_createProjectButton_clicked')
    def create_project(self):

        def do_create(project):
            self.app.ramsis_core.store.add(project)
            self.app.ramsis_core.store.save()
            self.ui.projectsTable.model().add_item(project)

        dlg = ProjectSettingsWindow(project=default_project())
        dlg.save_callback = do_create
        dlg.exec_()

    @pyqtSlot(name='on_openProjectButton_clicked')
    def open_project(self):
        idx = self.ui.projectsTable.selectionModel().selectedIndexes()[0]
        project = idx.data(CustomRoles.RepresentedItemRole)
        self.app.ramsis_core.open_project(project)
        self.close()

    def on_project_selection_changed(self, selected, deselected):
        if not selected.indexes():
            self._ui_state_machine.to_nothing_selected()
        else:
            idx = selected.indexes()[0]
            project = idx.data(CustomRoles.RepresentedItemRole)
            if project == self.app.ramsis_core.project:
                self._ui_state_machine.to_current_selected()
            else:
                self._ui_state_machine.to_other_selected()

    # UI state management

    def _load_projects(self):
        projects = self.app.ramsis_core.store.all_projects()
        vm = ProjectsTableModel(projects)
        self.ui.projectsTable.setModel(vm)
        self.ui.projectsTable.selectionModel().selectionChanged.connect(
            self.on_project_selection_changed
        )
