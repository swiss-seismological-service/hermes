from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt


class Node:
    """ Generic tree view node implementation """
    def __init__(self, item, parent_node):
        self.parent_node = parent_node
        self.item = item
        self.visible = True
        self.children = []

    def row(self):
        if self.parent_node:
            return self.parent_node.children.index(self)
        else:
            return 0

    def data(self, column, role):
        if role == Qt.DisplayRole and column == 0:
            return self.item

    def child(self, row):
        if self.children:
            return self.children[row]

    def child_count(self):
        return len(self.children)

    def column_count(self):
        return 1

    @property
    def root(self):
        node = self
        while node.parent_node:
            node = node.parent_node
        return node


# noinspection PyMethodOverriding
class TreeModel(QAbstractItemModel):

    def __init__(self, root_node, parent=None):
        super().__init__(parent)
        self.root_node = root_node

    def columnCount(self, index):
        if not index.isValid():
            return self.root_node.column_count()
        else:
            return index.internalPointer().column_count()

    def rowCount(self, parent):
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            parent_node = self.root_node
        else:
            parent_node = parent.internalPointer()
        return parent_node.child_count()

    def index(self, row, column, parent):
        if not parent.isValid():
            # we're at a top level node under root
            parent_node = self.root_node
        else:
            parent_node = parent.internalPointer()
        child_node = parent_node.child(row)
        if child_node:
            return self.createIndex(row, column, child_node)
        else:
            return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        node = index.internalPointer()
        parent_node = node.parent_node
        if parent_node == self.root_node:
            return QModelIndex()
        parent_row = parent_node.row()
        return self.createIndex(parent_row, 0, parent_node)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()
        data = node.data(index.column(), role)
        return data

    def headerData(self, column, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.root_node.data(column, role)
        return None
