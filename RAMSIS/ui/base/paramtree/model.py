"""
Parameter tree data model
    
Copyright (C) 2018, SED (ETH Zurich)

"""
from PyQt5.QtCore import Qt, QAbstractItemModel, QModelIndex
from ..roles import CustomRoles


class ParameterTreeModel(QAbstractItemModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_node = Node('root', parent_node=None)

    def columnCount(self, parent):
        return 2

    def rowCount(self, parent):
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            return self.root_node.child_count()
        node = parent.internalPointer()
        return node.child_count()

    def index(self, row, column, parent):
        if not parent.isValid():
            parent_node = self.root_node
        else:
            parent_node = parent.internalPointer()
        item = parent_node.child(row, column)
        return self.createIndex(row, column, item)

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        node = index.internalPointer()
        parent_node = node.parent_node
        if parent_node == self.root_node:
            return QModelIndex()
        else:
            return self.createIndex(parent_node.row(), 0, parent_node)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()
        data = node.data(index.column(), role)
        return data

    def headerData(self, column, orientation, role):
        if orientation != Qt.Horizontal:
            return None
        if role == Qt.DisplayRole:
            if column == 0:
                return 'Parameter'
            elif column == 1:
                return 'Value'
        return None

    def flags(self, index):
        default = super().flags(index)
        if index.column() == 0 or not self.parent(index).isValid():
            return default
        return Qt.ItemIsEditable | default

    def setData(self, index, value, role):
        node = index.internalPointer()
        if not isinstance(node, ParamNode):
            return False
        setattr(node.group, node.key, value)
        return True

    def insertRows(self, position, rows, parent_idx):
        parent_node = parent_idx.internalPointer() or self.root_node
        self.beginInsertRows(parent_idx, position, position + rows - 1)
        success = parent_node.insert_children(position, rows)
        self.endInsertRows()
        return success


class Node(object):

    def __init__(self, item, parent_node):
        self.parent_node = parent_node
        self.item = item
        self.visible = True
        self.children = []
        self._extend_node = None

    @property
    def extensible(self):
        return True if self._extend_node else False

    @extensible.setter
    def extensible(self, extensible):
        if not extensible:
            self._extend_node = None
        elif extensible and not self._extend_node:
            self._extend_node = ExtendNode(self)

    def child(self, row, _):
        if self.extensible and row == len(self.children):
            return self._extend_node
        else:
            return self.children[row]

    def child_count(self):
        count = len(self.children)
        if self.extensible:
            count += 1
        return count

    def row(self):
        if self.parent_node:
            return self.parent_node.children.index(self)
        else:
            return 0

    def data(self, column, role):
        """
        The default implementation returns the item itself for the display
        role and None for all other roles

        :param column: data column
        :param role: role
        :return: requested data

        """
        return None


class ExtendNode(Node):

    def __init__(self, parent_node):
        super().__init__(None, parent_node)



class GroupNode(Node):

    def __init__(self, item, parent_node):
        super().__init__(item, parent_node)

    def data(self, column, role):
        default = super().data(column, role)
        if role == Qt.DisplayRole:
            if column == 0:
                return str(self.item)
            else:
                return None
        elif role == CustomRoles.RepresentedItemRole:
            return self.item
        else:
            return default


class ParamNode(Node):
    def __init__(self, group, key, title, parent_node):
        super().__init__((group, key), parent_node)
        self.group = group
        self.key = key
        self.title = title

    def data(self, column, role):
        if role == Qt.DisplayRole:
            if column == 0:
                return self.title
            else:
                return getattr(self.group, self.key)
        elif role == CustomRoles.RepresentedItemRole:
            return self.item
        else:
            return None


