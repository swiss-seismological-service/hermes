# -*- encoding: utf-8 -*-
"""
Controller class for the stage status widget

Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED

"""

import os

from PyQt4 import QtGui, uic
from ramsisdata.calculationstatus import CalculationStatus
from ui.styles import STATUS_COLOR_ERROR, STATUS_COLOR_DISABLED

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

    def disable(self):
        self.ui.imageLabel.setPixmap(
            QtGui.QPixmap(':stage_images/images/stage_disabled.png')
        )
        self.ui.statusLabel.setText('Disabled')

    def plan(self):
        self.ui.imageLabel.setPixmap(
            QtGui.QPixmap(':stage_images/images/stage_planned.png')
        )
        self.ui.statusLabel.setText('Pending')

    def set_substages(self, substages):
        colors = {
            'Error': STATUS_COLOR_ERROR,
            'Disabled': STATUS_COLOR_DISABLED,
        }
        for i, stage in enumerate(substages):
            stage_label = QtGui.QLabel(stage[0])
            stage_label.setMinimumHeight(20)
            status_label = QtGui.QLabel(stage[1])
            status_label.setMinimumHeight(20)
            color = colors.get(stage[1], 'gray')
            status_label.setStyleSheet('color: {};'.format(color))
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

    def set_state(self, state):
        """
        Show the status of a calculation in this stage
        
        :param string state: Defined CalculationStatus state

        """
        if state == CalculationStatus.RUNNING:
            image = 'stage_running.png'
            text = 'Running'
        elif state == CalculationStatus.COMPLETE:
            image = 'stage_complete.png'
            text = 'Complete'
        elif state == CalculationStatus.ERROR:
            image = 'stage_error.png'
            text = 'Error'
        else:
            image = 'stage_other.png'
            text = '???'
        self.ui.imageLabel.setPixmap(
            QtGui.QPixmap(':/stage_images/images/{}'.format(image)))
        self.ui.statusLabel.setText(text)

