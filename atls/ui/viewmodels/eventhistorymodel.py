# -*- encoding: utf-8 -*-
"""
EventHistory based Qt view model
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from __future__ import absolute_import, unicode_literals, print_function
from PyQt4.QtCore import QAbstractListModel
import logging  # noqa


class EventListModel(QAbstractListModel):
    """
    A Qt List Model that binds to a SQL Alchemy query

    """
    def __init__(self, event_history, roles):
        super(EventListModel, self).__init__()
        self.event_history = event_history
        event_history.history_changed.connect(self._on_history_changed)
        self.roles = roles

        self.refresh()

    def rowCount(self, parent):
        return len(self.event_history)

    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self.event_history):
            return None

        elif role not in self.roles.keys():
            return None

        row = self.event_history[index.row()]
        return self.roles[role](row)

    def headerData(self):
        return None

    def refresh(self):
        self.layoutChanged.emit()

    def _on_history_changed(self, _):
        self.layoutChanged.emit()