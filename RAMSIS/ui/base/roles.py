# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Custom roles definitions
"""

from PyQt5.QtCore import Qt


class CustomRoles:
    """
    Additional custom roles to standard Qt roles

    """
    FilterCriteriaRole = Qt.UserRole + 1
    RepresentedItemRole = Qt.UserRole + 2
    SortRole = Qt.UserRole + 3
