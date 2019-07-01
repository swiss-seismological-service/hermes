# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Base TreeView class and associated view layer classes

"""

from PyQt5.QtWidgets import QTreeView
from RAMSIS.ui.base.contextaction import ContextActionMixin


class TreeView(ContextActionMixin, QTreeView):
    """ Context Action enabled QTreeView """
    pass
