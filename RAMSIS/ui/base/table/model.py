# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Base TableView model class and associated model layer classes
"""

import dateutil.parser
from datetime import datetime
from sqlalchemy.orm import object_session
from sqlalchemy.inspection import inspect
import sqlalchemy.types
from PyQt5.QtCore import Qt, QAbstractTableModel, QSortFilterProxyModel, \
    QModelIndex
from PyQt5.QtGui import QFont
from RAMSIS.utils import rgetattr, rsetattr
from ..roles import CustomRoles


class TableModel(QAbstractTableModel):

    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items
        self.columns = []

    def columnCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.columns)

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.items)

    def flags(self, index):
        flags = super().flags(index)
        if self.columns[index.column()].editable:
            flags |= Qt.ItemIsEditable
        return flags

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Vertical:
            return None
        else:
            if role == Qt.DisplayRole:
                return self.columns[section].title
            elif role == CustomRoles.RepresentedItemRole:
                return self.columns[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        row_idx, col_idx = index.row(), index.column()
        col = self.columns[col_idx]
        item = self.items[row_idx]
        if role in col.supported_roles:
            return col.data(item, role)
        elif role == CustomRoles.RepresentedItemRole:
            return item

    def setData(self, index, value, role):
        row_idx, col_idx = index.row(), index.column()
        col = self.columns[col_idx]
        if not col.editable:
            return False
        if role == Qt.EditRole:
            item = self.items[row_idx]
            if col.set_value(item, value):
                self.dataChanged.emit(index, index)
                return True
        return False

    def add_item(self, item):
        idx = len(self.items)
        self.beginInsertRows(QModelIndex(), idx, idx)
        self.items.append(item)
        self.endInsertRows()

    def remove_item(self, item):
        idx = self.items.index(item)
        self.beginRemoveRows(QModelIndex(), idx, idx)
        self.items.remove(item)
        self.endRemoveRows()


class SelectableColumnsSortFilterProxyModel(QSortFilterProxyModel):

    def __init__(self, source_model, parent=None):
        super(SelectableColumnsSortFilterProxyModel, self).__init__(parent)
        self.setSourceModel(source_model)
        self.setSortRole(CustomRoles.SortRole)
        self.setDynamicSortFilter(True)

    def hide_column(self, col, hide):
        col.hidden = hide
        self.invalidateFilter()

    def filterAcceptsColumn(self, source_column, source_parent):
        return not self.sourceModel().columns[source_column].hidden


class TableColumn:

    def __init__(self, name, attr=None, title=None, hidden=False,
                 editable=False, width=None, primary=False,
                 initial_order=None):
        self.name = name
        self.attr = attr or name.lower().replace(' ', '_')
        self.hidden = hidden
        self.title = title or name
        self.primary = primary
        self.editable = editable
        self.width = width
        self.initial_order = initial_order

    @property
    def supported_roles(self):
        return [Qt.DisplayRole, CustomRoles.SortRole, Qt.FontRole, Qt.EditRole]

    def data(self, obj, role):
        data = rgetattr(obj, self.attr, '')
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if not data:
                return None
            elif isinstance(data, datetime):
                return data.strftime('%d.%m.%Y')
            else:
                return str(data)
        elif role == CustomRoles.SortRole:
            if isinstance(data, datetime):
                return data.timestamp()
            else:
                return data or ''
        elif role == Qt.FontRole and self.primary:
            font = QFont()
            font.setBold(True)
            return font

    def set_value(self, obj, value):
        if self.editable:
            try:
                col_type = inspect(obj).mapper.columns[self.attr].type
            except KeyError:
                pass
            else:
                # Basic value interpretation
                if value and isinstance(value, str) and \
                        isinstance(col_type, sqlalchemy.types.DateTime):
                    try:
                        value = dateutil.parser.parse(value, dayfirst=True)
                    except ValueError:
                        return False
            rsetattr(obj, self.attr, value or None)
            object_session(obj).commit()
            return True

    def __repr__(self):
        return f'<TableColumn "{self.name}" at {id(self):x}>'
