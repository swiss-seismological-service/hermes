# -*- encoding: utf-8 -*-
"""
Qt data models that bind to SQLAlchemy queries

We don't currently use this in RAMSIS but it might come in handy at some point.
Note that we use PyQt API version 2, so those QVariants should be replaced
with their respective python types.


© 2013 Mark Harviston, BSD License

"""

from __future__ import absolute_import, unicode_literals, print_function
from PyQt4 import QtGui
from PyQt4.QtCore import QAbstractListModel, QAbstractTableModel, QVariant, Qt
import logging  # noqa


class AlchemicalListModel(QAbstractListModel):
    """
    A Qt List Model that binds to a SQL Alchemy query

    """
    def __init__(self, session, query, roles):
        super(AlchemicalListModel, self).__init__()
        self.session = session
        self.query = query
        self.roles = roles

        self.results = None

        self.refresh()

    def rowCount(self, parent):
        return self.query.count()

    def data(self, index, role):
        if not index.isValid() or index.row() >= self.query.count():
            return QVariant()

        elif role not in self.roles.keys():
            return QVariant()

        row = self.results[index.row()]
        return self.roles[role](row)

    def headerData(self):
        return QVariant()

    def refresh(self):
        self.results = self.query.all()
        self.layoutChanged.emit()


class AlchemicalTableModel(QAbstractTableModel):
    """
    A Qt Table Model that binds to a SQL Alchemy query

    Example:
    >>> model = AlchemicalTableModel(Session, [('Name', Entity.name)])
    >>> table = QTableView(parent)
    >>> table.setModel(model)

    """

    def __init__(self, session, query, columns):
        super(AlchemicalTableModel, self).__init__()
        # TODO self.sort_data = None
        self.session = session
        self.fields = columns
        self.query = query

        self.results = None
        self.count = None
        self.sort = None
        self.filter = None

        self.refresh()

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.fields[col][0])
        return QVariant()

    def setFilter(self, filter):
        """Sets or clears the filter, clear the filter by setting to None"""
        self.filter = filter
        self.refresh()

    def refresh(self):
        """Recalculates, self.results and self.count"""

        self.layoutAboutToBeChanged.emit()

        q = self.query
        if self.sort is not None:
            order, col = self.sort
            col = self.fields[col][1]
            if order == Qt.DescendingOrder:
                col = col.desc()
        else:
            col = None

        if self.filter is not None:
            q = q.filter(self.filter)

        q = q.order_by(col)

        self.results = q.all()
        self.count = q.count()
        self.layoutChanged.emit()

    def flags(self, index):
        _flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable

        if self.sort is not None:
            order, col = self.sort

            if self.fields[col][3].get('dnd', False) and index.column() == col:

                _flags |= Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled

        if self.fields[index.column()][3].get('editable', False):
            _flags |= Qt.ItemIsEditable

        return _flags

    def supportedDropActions(self):
        return Qt.MoveAction

    def dropMimeData(self, data, action, row, col, parent):
        if action != Qt.MoveAction:
            return

        return False

    def rowCount(self, parent):
        return self.count or 0

    def columnCount(self, parent):
        return len(self.fields)

    def data(self, index, role):
        if not index.isValid():
            return QVariant()

        elif role not in (Qt.DisplayRole, Qt.EditRole):
            return QVariant()

        row = self.results[index.row()]
        name = self.fields[index.column()][2]

        return unicode(getattr(row, name))

    def setData(self, index, value, role=None):
        row = self.results[index.row()]
        name = self.fields[index.column()][2]

        try:
            setattr(row, name, value.toString())
            self.session.commit()
        except Exception as ex:
            QtGui.QMessageBox.critical(None, 'SQL Error', unicode(ex))
            return False
        else:
            self.dataChanged.emit(index, index)
            return True

    def sort(self, col, order):
        """Sort table by given column number."""
        self.sort = order, col
        self.refresh()
