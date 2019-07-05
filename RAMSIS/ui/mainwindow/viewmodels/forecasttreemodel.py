# Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED
"""
A view model to display forecasts and their scenarios in a tree view

The tree view has the following structure:

    root_node (not visible)
      Forecast 06:00
        Scenario 1
        Scenario 2
      Forecast 12:00
        Scenario 1
        ...

"""

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt, QSize
from PyQt5.QtGui import QBrush, QFont
from RAMSIS.ui.base.tree.model import TreeModel, Node
from RAMSIS.ui.base.utils import utc_to_local


COLUMNS = ('FC / Scenario', 'Status')


class ScenarioNode(Node):
    """
    Node representing a scenario

    The :ivar:`Node.item` here is a
    :class:`ramsis.datamodel.forecast.ForecastScenario`.
    """

    def data(self, column, role):
        default = super(ScenarioNode, self).data(column, role)
        if column == 0:
            if role == Qt.DisplayRole:
                # TODO LH: we could define __str__ on the model entities
                return self.item.name
        if column == 1:
            if role == Qt.DisplayRole:
                # TODO LH: this doesn't exist in the new model atm
                #return self.item.summary_status
                return 'n/a'
            elif role == Qt.ForegroundRole:
                return QBrush(Qt.gray)
            elif role == Qt.FontRole:
                font = QFont()
                font.setItalic(True)
                return font
        else:
            return default


class ForecastNode(Node):
    """
    Node representing a forecast at a specific time

    The :ivar:`Node.item` here is a
    :class:`ramsis.datamodel.forecast.Forecast`.

    """
    def __init__(self, forecast, parent_node):
        """
        :param Forecast forecast: Forecast object represented by this node
        :param Node parent_node: Parent Node (root node)
e
        """
        super().__init__(forecast, parent_node)
        self.children = [ScenarioNode(s, self) for s in self.item.scenarios]

    def data(self, column, role):
        default = super().data(column, role)
        if role == Qt.DisplayRole and column == 0:
            local = utc_to_local(self.item.starttime)
            return local.strftime('%Y-%m-%d %H:%M')
        return default


class ForecastsRootNode(Node):
    """
    This is the (invisible) root node.

    The root node just provides the header data for the tree view.
    """

    def __init__(self, project):
        super().__init__(COLUMNS, parent_node=None)
        self.children = [ForecastNode(f, self) for f in project.forecasts]


class ForecastTreeModel(TreeModel):

    def __init__(self, project):
        self.project = project
        self.root_node = ForecastsRootNode(project)
        super(ForecastTreeModel, self).__init__(root_node=self.root_node)

    def add_forecast(self, forecast):
        row = self.project.forecasts.index(forecast)
        node = ForecastNode(forecast, self.root_node)
        self.insert_nodes(self.root_node, row, [node])