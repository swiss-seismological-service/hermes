"""
Base TableView class and associated view layer classes
    
Copyright (C) 2018, SED (ETH Zurich)

"""
from PyQt5.QtCore import QObject, Qt, QSortFilterProxyModel
from PyQt5.QtWidgets import QMenu, QAction, QTableView, QStyledItemDelegate
from PyQt5.QtGui import QCursor
from RAMSIS.ui.base.contextaction import ContextActionMixin
from RAMSIS.ui.base.roles import CustomRoles


class TableView(ContextActionMixin, QTableView):
    """
    Base class for tables used throughout the app

    This table class provides a number of standard features which are used
    throughout the extension. These include:

    - User hideable columns
    - Support for context actions

    Dependencies:

    - requires a SelectableColumnsSortFilterProxyModel as it's view model

    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    @property
    def source_model(self):
        """ A shortcut to the base data model """
        return self.model().sourceModel()

    def setModel(self, model):
        super().setModel(model)
        headers = self.horizontalHeader()
        headers.setContextMenuPolicy(Qt.CustomContextMenu)
        headers.customContextMenuRequested.connect(
            self.on_header_ctx_menu_requested)
        column_role = CustomRoles.RepresentedItemRole
        visible_columns = [model.headerData(i, Qt.Horizontal, role=column_role)
                           for i in range(self.horizontalHeader().count())]
        for column in reversed(visible_columns):
            idx = visible_columns.index(column)
            if column.width:
                self.setColumnWidth(idx, column.width)
            if column.initial_order is not None:
                self.sortByColumn(idx, column.initial_order)

    def on_header_ctx_menu_requested(self):
        menu = ColumnSelectorMenu(self.model())
        menu.show(QCursor.pos())


class ColumnSelectorMenu(QObject):
    """
    A menu to show/hide columns in a table

    """
    def __init__(self, table_model):
        super(ColumnSelectorMenu, self).__init__()
        self.table_model = table_model
        self.menu = QMenu()
        columns = table_model.sourceModel().columns
        selectable = (c for c in columns if not c.primary)
        for column in selectable:
            action = QAction(column.name, parent=self)
            action.setData(columns.index(column))
            action.setCheckable(True)
            action.setChecked(not column.hidden)
            action.triggered.connect(self.on_column_selection_changed)
            self.menu.addAction(action)

    def show(self, pos):
        self.menu.exec(pos)

    def on_column_selection_changed(self):
        action = self.sender()
        idx = action.data()
        column = self.table_model.sourceModel().columns[idx]
        self.table_model.hide_column(column, not action.isChecked())


class TableDelegate(QStyledItemDelegate):

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model

    def table_column(self, index):
        if isinstance(self.model, QSortFilterProxyModel):
            source_index = self.model.mapToSource(index)
            return self.model.sourceModel().columns[source_index.column()]
        else:
            return self.model.columns[index.column()]
