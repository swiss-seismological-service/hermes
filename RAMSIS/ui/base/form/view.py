# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
A form built from a two column table
"""

from PyQt5.QtWidgets import QTableView, QAbstractItemView, \
    QHeaderView


class FormTableView(QTableView):

    def __init__(self, *args):
        super().__init__(*args)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers |
                             QAbstractItemView.DoubleClicked)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().\
            setSectionResizeMode(QHeaderView.ResizeToContents)

    def setModel(self, model):
        super().setModel(model)
        self.horizontalHeader().setStretchLastSection(True)
