# -*- encoding: utf-8 -*-
"""
A view model to display forecast_set and scenarios in a tree view

The tree view has the following structure:

    root_node
      Forecast 06:00
        Scenario 1
        Scenario 2
      Forecast 12:00
        Scenario 1
        ...

Copyright (C) 2016, SED (ETH Zurich)

"""

from PyQt4.QtCore import QAbstractItemModel, QModelIndex, Qt, QSize
from PyQt4.QtGui import QPixmap, QCheckBox


# class ProjectRole:
#     """
#     Additional custom roles
#     """
#     RepresentedItemRole = Qt.UserRole + 1


class Node(object):
    """
    Parent class for all node types

    A node represents an item in the tree

    """
    def __init__(self, item, parent_node):
        self.parent_node = parent_node
        self.item = item
        self.visible = True

    def data(self, column, role):
        """
        The default implementation returns the item itself for the display
        role and None for all other roles
        :param column: data column
        :param role: role
        :return: requested data
        """
        return None

    def child_count(self):
        return 0


class ScenarioNode(Node):

    def data(self, column, role):
        default = super(ScenarioNode, self).data(column, role)
        if role == Qt.DisplayRole and column == 0:
            return self.item.name
#        elif role == ProjectRole.RepresentedItemRole:
#            return self.item
        elif role == Qt.CheckStateRole and column == 1:
            return Qt.Checked if self.visible else Qt.Unchecked
        else:
            return default


# class GridNode(Node):
#
#     def data(self, column, role):
#         default = super(GridNode, self).data(column, role)
#         if role == Qt.DisplayRole:
#             return self.item.name if column == 0 else None
#         elif role == ProjectRole.RepresentedItemRole:
#             return self.item
#         elif role == Qt.CheckStateRole and column == 1:
#             return Qt.Checked if self.visible else Qt.Unchecked
#         else:
#             return default


class ForecastNode(Node):
    """ Represents a forecast at a specific time """
    def __init__(self, forecast, parent_node):
        """
        :param Forecast forecast: Forecast object represented by this node
        :param Node parent_node: Parent Node (root node)
e
        """
        super(ForecastNode, self).__init__(forecast, parent_node)
        scenarios = self.item.input.scenarios
        self.children = [ScenarioNode(s, self) for s in scenarios]

    def child(self, row, column):
        return self.children[row]

    def child_count(self):
        return len(self.children)

    def data(self, column, role):
        default = super(ForecastNode, self).data(column, role)
        if role == Qt.DisplayRole:
            return self.item.forecast_time.strftime('%d.%m.%Y %H:%M') \
                if column == 0 else None
        elif role == Qt.DecorationRole:
            return None #QPixmap(':/small/catalog') if column == 0 else None
        else:
            return default

    def insert_children(self, position, rows):
        inserted_scenarios = self.item.scenarios[position:position + rows]
        for i, scenario in enumerate(inserted_scenarios):
            self.children.insert(position + i, ScenarioNode(scenario, self))


# class ManualSectionNode(Node):
#     """ Section node for manually planned forecast_set """
#     def __init__(self, project, parent_node):
#         """
#         :param project: PyMap project from which grids will be served
#         :type project: Project
#         :param parent: Parent Node (root node)
#         :type parent: Node
#         """
#         super(ManualSectionNode, self).__init__('Grids', parent_node)
#         self.project = project
#         self.children = []
#         self.refresh_grids()
#
#     def child(self, row, column):
#         return self.children[row]
#
#     def child_count(self):
#         return len(self.children)
#
#     def data(self, column, role):
#         default = super(ManualSectionNode, self).data(column, role)
#         if role == Qt.DisplayRole:
#             return self.item if column == 0 else None
#         elif role == Qt.DecorationRole:
#             return QPixmap(':/small/grid') if column == 0 else None
#         else:
#             return default
#
#     def refresh_grids(self):
#         self.children = [GridNode(g, self) for g in self.project.grids]


class ForecastTreeModel(QAbstractItemModel):

    #AUTOMATIC_SECTION = 0
    #MANUAL_SECTION = 1

    def __init__(self, forecast_set):
        """
        :param project:
        :tyape project: Project
        :return:
        """
        super(ForecastTreeModel, self).__init__(parent=None)
        self.root_node = Node('Forecasts', parent_node=None)
        self.forecast_set = forecast_set
#       self.project.catalogs_changed.connect(self.on_catalogs_changed)
        self.forecast_nodes = [ForecastNode(f, self.root_node)
                               for f in self.forecast_set.forecasts]
#        self.sections = [AutomaticSectionNode(forecast_set, self.root_node),
#                         ManualSectionNode(forecast_set, self.root_node)]

    def columnCount(self, parent):
        return 2

    def rowCount(self, parent):
        if not parent.isValid():
            return len(self.forecast_nodes)
        if parent.column() > 0:
            return 0
        node = parent.internalPointer()
        return node.child_count()

    def index(self, row, column, parent):
        if not parent.isValid():
            # we're at the root node
            item = self.forecast_nodes[row]
        else:
            item = parent.internalPointer().child(row, column)
        return self.createIndex(row, column, item)

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        node = index.internalPointer()
        parent_node = node.parent_node
        if parent_node == self.root_node:
            return QModelIndex()
        node_idx = self.forecast_nodes.index(parent_node)
        return self.createIndex(node_idx, 0, parent_node)

    def data(self, index, role):
        if not index.isValid():
            return None
        node = index.internalPointer()
        data = node.data(index.column(), role)
        return data

    def setData(self, index, value, role):
        if role == Qt.CheckStateRole:
            node = index.internalPointer()
            node.visible = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index):
        return Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | \
               Qt.ItemIsEnabled | Qt.ItemIsEditable

    def headerData(self, column, orientation, role):
        if orientation != Qt.Horizontal:
            return None
        if role == Qt.DisplayRole:
            if column == 0:
                return 'Forecast'
            elif column == 1:
                return 'Visible'
        elif role == Qt.SizeHintRole:
            if column == 0:
                return QSize(152, 20)
        return None

    def insertRows(self, position, rows, parent_idx):
        parent_node = parent_idx.internalPointer()
        self.beginInsertRows(parent_idx, position, position + rows - 1)
        success = parent_node.insert_children(position, rows)
        self.endInsertRows()
        return success

    # Signal slots
    # def on_catalogs_changed(self, changes):
    #     catalog_node = self.sections[self.CATALOG_SECTION]
    #     parent_idx = self.createIndex(self.CATALOG_SECTION, 0, catalog_node)
    #     inserted_catalogs = changes['inserted']
    #     for catalog in inserted_catalogs:
    #         position = self.project.catalogs.index(catalog)
    #         self.insertRows(position, 1, parent_idx)