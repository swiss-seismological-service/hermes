"""
Custom roles definitions
    
Copyright (C) 2018, SED (ETH Zurich)

"""
from PyQt5.QtCore import Qt


class CustomRoles:
    """
    Additional custom roles to standard Qt roles

    """
    FilterCriteriaRole = Qt.UserRole + 1
    RepresentedItemRole = Qt.UserRole + 2
    SortRole = Qt.UserRole + 3
