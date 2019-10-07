# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Controller class for the traffic light widget
"""

import os

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget

from RAMSIS.ui.utils import UiForm


FORM_BASE_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'views')


def _pixmap(name):
    return QPixmap(':/traffic_light/images/' + name)


class TrafficLightWidget(
        QWidget, UiForm('trafficlight.ui', form_base_path=FORM_BASE_PATH)):

    def red(self):
        self.off()
        self.ui.topLabel.setPixmap(_pixmap('tl_red.png'))

    def yellow(self):
        self.off()
        self.ui.midLabel.setPixmap(_pixmap('tl_yellow.png'))

    def green(self):
        self.off()
        self.ui.bottomLabel.setPixmap(_pixmap('tl_green.png'))

    def off(self):
        off_img = _pixmap('tl_off.png')
        self.ui.topLabel.setPixmap(off_img)
        self.ui.midLabel.setPixmap(off_img)
        self.ui.bottomLabel.setPixmap(off_img)
