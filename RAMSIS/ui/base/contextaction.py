# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Actions installed in context menus for TableView rows
"""

from PyQt5.QtWidgets import QAction, QMessageBox, QMenu
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt

from RAMSIS.ui.base.roles import CustomRoles


class ContextActionMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context_actions = []
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(
            self.on_context_actions_menu_requested)

    def on_context_actions_menu_requested(self, pos):
        indexes = [idx for idx in self.selectionModel().selectedIndexes()
                   if idx.column() == 0]
        menu = QMenu()
        for action in self.context_actions:
            if action.isSeparator():
                menu.addSeparator()
            else:
                action.selected_indexes = indexes
                menu.addAction(action)
        if menu.actions():
            menu.exec(QCursor.pos())


class ContextAction(QAction):

    def __init__(self, text, slot, enabler=None):
        super().__init__(text)
        self.triggered.connect(self._on_triggered)
        self._enabler = enabler if enabler else lambda idx: True
        self.slot = slot
        self._selected_indexes = []

    @property
    def selected_indexes(self):
        return self._selected_indexes

    @selected_indexes.setter
    def selected_indexes(self, indexes):
        self._selected_indexes = indexes
        self.setEnabled(self._enabler(indexes))

    def confirm(self, indexes):
        return True

    def _on_triggered(self):
        if self.confirm(self.selected_indexes):
            self.slot(self.selected_indexes)

    # Enablers

    # TODO(damb): If cls is not used - make it static
    @classmethod
    def single_only_enabler(self, idx):
        return len(idx) == 1


class Separator(ContextAction):

    def __init__(self, parent=None):
        super().__init__('', slot=None)

    def isSeparator(self):
        return True


class ContextActionDelete(ContextAction):

    def __init__(self, slot, parent_widget, text='Delete...', enabler=None,
                 target='items'):
        super().__init__(text, slot, enabler=enabler)
        self.target = target
        self.parent_widget = parent_widget

    def confirm(self, indexes):
        if len(indexes) > 1:
            what = f'all selected {self.target}'
        else:
            what = str(indexes[0].data(CustomRoles.RepresentedItemRole))
        reply = QMessageBox.critical(self.parent_widget,
                                     f'Delete {self.target}',
                                     f'Are you sure you want to delete '
                                     f'{what}?',
                                     QMessageBox.Yes, QMessageBox.No)
        return reply == QMessageBox.Yes
