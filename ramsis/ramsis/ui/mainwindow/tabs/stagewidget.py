# -*- encoding: utf-8 -*-
"""
Controller class for the stage status widget

Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED

"""

import os

from PyQt4 import QtGui, uic

ui_path = os.path.dirname(__file__)
STAGE_WIDGET_PATH = os.path.join(ui_path, '..', '..', 'views',
                                 'stagestatus.ui')
Ui_StageWidget = uic.loadUiType(STAGE_WIDGET_PATH)[0]


class StageWidget(QtGui.QWidget):

    def __init__(self, title, **kwargs):
        super(StageWidget, self).__init__(**kwargs)

        # Setup the user interface
        self.ui = Ui_StageWidget()
        self.ui.setupUi(self)
        self.ui.titleLabel.setText(title)
        self.clear_substages()

    def set_substages(self, substages):
        for i, stage in enumerate(substages):
            stage_label = QtGui.QLabel(stage[0])
            status_label = QtGui.QLabel(stage[1])
            status_label.setStyleSheet('color: gray;')
            self.ui.substatusLayout.addWidget(stage_label, i, 0)
            self.ui.substatusLayout.addWidget(status_label, i, 1)

    def clear_substages(self):
        columns = self.ui.substatusLayout.columnCount()
        rows = self.ui.substatusLayout.rowCount()

        for j in range(columns):
            for i in range(rows):
                item = self.ui.substatusLayout.itemAtPosition(i, j)
                if item is None:
                    continue
                item.widget().setParent(None)

    def set_status(self, status):
        if status == 'running':
            self.ui.imageLabel.setPixmap(QtGui.QPixmap(':/stage_images/images/stage_running.png'))
            self.ui.statusLabel.setText('Running')

