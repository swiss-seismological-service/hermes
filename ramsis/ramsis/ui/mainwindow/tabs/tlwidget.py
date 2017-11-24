# -*- encoding: utf-8 -*-
"""
Controller class for the traffic light widget

Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED

"""

import os

from PyQt5 import uic
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget

ui_path = os.path.dirname(__file__)
TL_WIDGET_PATH = os.path.join(ui_path, '..', '..', 'views',
                                 'trafficlight.ui')
Ui_TlWidget = uic.loadUiType(TL_WIDGET_PATH)[0]


def _pixmap(name):
    return QPixmap(':/traffic_light/images/' + name)


class TrafficLightWidget(QWidget):

    def __init__(self, **kwargs):
        super(TrafficLightWidget, self).__init__(**kwargs)
        # Setup the user interface
        self.ui = Ui_TlWidget()
        self.ui.setupUi(self)

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


