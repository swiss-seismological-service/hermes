# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Controller class for the stage status widget
"""

import os

from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import QWidget, QLabel
from RAMSIS.ui.utils import UiForm

FORM_BASE_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'views')


class StageWidget(
        QWidget, UiForm('stagestatus.ui', form_base_path=FORM_BASE_PATH)):

    colors = {
        'COMPLETE': 'green',
        'DISABLED': 'gray',
        'RUNNING': 'black',
        'ERROR': 'red',
        'PENDING': 'orange',
        'DISPATCHED': 'purple',
        'ONHOLD': 'brown',
        'PREPARED': 'blue'
    }

    def __init__(self, title, **kwargs):
        super().__init__(**kwargs)

        self.ui.titleLabel.setText(title)
        self.clear_substages()
        self.ui.stageReset.hide()
        self.hazard_reset_button_connected = False

    def disable(self):
        self.ui.imageLabel.setPixmap(
            QPixmap(':stage_images/images/stage_disabled.png')
        )
        self.ui.statusLabel.setText('DISABLED')

    def plan(self):
        self.ui.imageLabel.setPixmap(
            QPixmap(':stage_images/images/stage_planned.png')
        )
        self.ui.statusLabel.setText('PENDING')

    def set_stage_status(self, status):
        self.ui.statusLabel.setText(str(status))
        color = self.colors.get(status, 'gray')
        self.ui.statusLabel.setStyleSheet('color: {}'.format(color))

    def set_substages(self, substages):

        for i, stage in enumerate(substages):
            stage_label = QLabel(stage[0])
            stage_label.setMinimumHeight(20)
            status_label = QLabel(stage[1])
            status_label.setMinimumHeight(20)
            color = self.colors.get(stage[1], 'gray')
            status_label.setStyleSheet('color: {};'.format(color))
            self.ui.substatusLayout.addWidget(stage_label, i, 0)
            self.ui.substatusLayout.addWidget(status_label, i, 1)

    def set_aggregate_substages(self, substages):
        title1 = QLabel('Status')
        title2 = QLabel('Hazard Run Count')

        title1.setFont(QFont("SansSerif", weight=QFont.Bold))
        title2.setFont(QFont("SansSerif", weight=QFont.Bold))
        self.ui.substatusLayout.addWidget(title1, 0, 0)
        self.ui.substatusLayout.addWidget(title2, 0, 1)
        for ind, stage in enumerate(substages):
            i = ind + 1
            state_label = QLabel(stage[0])
            state_label.setMinimumHeight(20)
            count_label = QLabel(str(stage[1]))
            count_label.setMinimumHeight(20)
            color = self.colors.get(stage[0], 'gray')
            state_label.setStyleSheet('color: {};'.format(color))
            self.ui.substatusLayout.addWidget(state_label, i, 0)
            self.ui.substatusLayout.addWidget(count_label, i, 1)

    def clear_substages(self):
        columns = self.ui.substatusLayout.columnCount()
        rows = self.ui.substatusLayout.rowCount()

        for j in range(columns):
            for i in range(rows):
                item = self.ui.substatusLayout.itemAtPosition(i, j)
                if item is None:
                    continue
                if item.widget() is None:
                    continue
                item.widget().setParent(None)

    def set_state(self, state):
        """
        Show the status of a calculation in this stage

        :param string state: Defined CalculationStatus state

        """
        # TODO: reimplement
        pass
        # if state == CalculationStatus.RUNNING:
        #     image = 'stage_running.png'
        #     text = 'Running'
        # elif state == CalculationStatus.COMPLETE:
        #     image = 'stage_complete.png'
        #     text = 'Complete'
        # elif state == CalculationStatus.ERROR:
        #     image = 'stage_error.png'
        #     text = 'Error'
        # else:
        #     image = 'stage_other.png'
        #     text = '???'
        # self.ui.imageLabel.setPixmap(
        #     QPixmap(':/stage_images/images/{}'.format(image)))
        # self.ui.statusLabel.setText(text)
