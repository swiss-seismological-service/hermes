"""
A form model for SQLAlchemy object based forms
    
Copyright (C) 2018, SED (ETH Zurich)

"""
import dateutil
from datetime import datetime
from PyQt5.QtCore import Qt, QAbstractTableModel
from PyQt5.QtGui import QFont
import sqlalchemy
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import object_session
from RAMSIS.utils import rgetattr, rsetattr


class SQLAObjectFormModelField:

    def __init__(self, title, attr, editable=True):
        self.title = title
        self.attr = attr
        self.editable = editable

    def value(self, obj, default=None):
        value = rgetattr(obj, self.attr, default)
        if isinstance(value, datetime):
            return value.strftime('%d.%m.%Y')
        return value

    def set_value(self, obj, value):
        if self.editable:
            try:
                col_type = inspect(obj).mapper.columns[self.attr].type
            except KeyError:
                pass
            else:
                # Basic value interpretation
                if isinstance(value, str) \
                        and isinstance(col_type, sqlalchemy.types.DateTime):
                    value = dateutil.parser.parse(value, dayfirst=True)
                    if not value:
                        return False
            rsetattr(obj, self.attr, value or None)
            object_session(obj).commit()
            return True


class SQLAObjectFormModel(QAbstractTableModel):

    def __init__(self, obj, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields = []
        self.obj = obj

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.fields)

    def columnCount(self, parent):
        if parent.isValid():
            return 0
        return 2

    def data(self, index, role):
        row, col = index.row(), index.column()
        if role == Qt.DisplayRole or role == Qt.EditRole:
            field = self.fields[row]
            if col == 0:
                return field.title
            else:
                return field.value(self.obj)
        elif role == Qt.FontRole:
            if col == 0:
                bold = QFont()
                bold.setBold(True)
                return bold

    def setData(self, index, value, role):
        row, col = index.row(), index.column()
        if col == 0 or not self.fields[row].editable:
            return False
        if role == Qt.EditRole:
            if self.fields[row].set_value(self.obj, value):
                self.dataChanged.emit(index, index)
                return True

    def flags(self, index):
        flags = super().flags(index)
        if index.column() == 1:
            if self.fields[index.row()].editable:
                flags |= Qt.ItemIsEditable
            else:
                flags &= ~Qt.ItemIsEnabled
        return flags


