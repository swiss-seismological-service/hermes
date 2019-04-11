"""
Short Description
    
Copyright (C) 2018, SED (ETH Zurich)

"""
from PyQt5.QtCore import Qt, QAbstractTableModel
from PyQt5.QtGui import QFont


class FormTableModel(QAbstractTableModel):
    """
    An abstract model to display fields and values in a two column table
    (i.e. something like a dynamic form view)

    :ivar list fields: A list of {'title': title, 'value': value} dicts

    """

    def __init__(self, parent=None):
        super(FormTableModel, self).__init__(parent)
        self.fields = []

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
        if role == Qt.DisplayRole:
            field = self.fields[row]
            if col == 0:
                return field['title']
            else:
                return field['value']
        elif role == Qt.FontRole:
            if col == 0:
                bold = QFont()
                bold.setBold(True)
                return bold

    def flags(self, index):
        flags = super().flags(index)
        if index.column() == 1:
            flags |= Qt.ItemIsEnabled | Qt.ItemIsEditable
        return flags
