# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
TreeView model facilities.
"""

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt
from RAMSIS.ui.base.roles import CustomRoles


class Node:
    """ Generic tree view node implementation """
    def __init__(self, item, parent_node):
        self.parent_node = parent_node
        self.item = item
        self.visible = True
        self.children = []

    def row(self):
        """ return our row position under parent """
        if self.parent_node:
            return self.parent_node.children.index(self)
        else:
            return 0

    def data(self, column, role):
        """
        Return the display data for this node

        The default implementation only supports
        :cvar:`~PyQt5.QtCore.Qt.DisplayRole` and
        :cvar:~`RAMSIS.ui.base.roles.CustomRoles.RepresentedItemRole`. If the
        item can be represented as a string it will return that for column 0.
        If it can index the item it will return string representations for
        higher column numbers too.

        :param int column: Column index to get data for
        :param role: Requested Qt role
        """
        if role == CustomRoles.RepresentedItemRole:
            return self.item
        elif role == Qt.DisplayRole:
            if isinstance(self.item, str):
                return self.item if column == 0 else None
            else:
                try:
                    return str(self.item[column])
                except TypeError:
                    return str(self.item) if column == 0 else None

    def child(self, row):
        if self.children:
            return self.children[row]

    def child_count(self):
        return len(self.children)

    def column_count(self):
        """
        Return the number of columns to display at this node

        The default implementation will return 1 if the item is a string and
        `len(self.item)` if the item supports that. Otherwise it will return 1.

        :return: Number of columns to display
        """
        if isinstance(self.item, str):
            return 1
        else:
            try:
                return len(self.item)
            except TypeError:
                return 1

    @property
    def root(self):
        node = self
        while node.parent_node:
            node = node.parent_node
        return node

    def index_path(self):
        path = []
        node = self
        while node.parent_node:
            path.insert(0, node.row())
            node = node.parent_node
        return path


class TreeModel(QAbstractItemModel):
    """
    Generic tree model implementation

    The tree model's structure is implemented with :class:`Node` objects and
    their children. I.e. each index points at a node and the node's
    :ivar:`~Node.item` has the actual data for the row at the nodes position.
    The :ivar:`root_node` is not visible as a node but provides the header data
    for the tree view.

    .. note::
        The implementation is similar to the "editabletreemodel" example in the
        Qt docs where the Nodes are called Items (here, "Items" are the domain
        model objects that provide the data for a Node).

    """

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
            node = self.root_node
        else:
            node = index.internalPointer()
        data = node.data(index.column(), role)
        return data

    def headerData(self, column, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.root_node.data(column, role)
        return None

    def insert_nodes(self, parent_node, pos, nodes):
        index_path = parent_node.index_path()
        parent_idx = QModelIndex()
        for row in index_path:
            parent_idx = self.index(row, 0, parent_idx)
        self.beginInsertRows(parent_idx, pos, pos + len(nodes) - 1)
        parent_node.children[pos:pos] = nodes
        self.endInsertRows()

    def remove_node(self, node):
        index_path = node.parent_node.index_path()
        parent_idx = QModelIndex()
        for row in index_path:
            parent_idx = self.index(row, 0, parent_idx)
        row = node.row()
        self.beginRemoveRows(parent_idx, row, row)
        node.parent_node.children.remove(node)
        self.endRemoveRows()
