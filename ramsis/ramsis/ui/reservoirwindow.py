# -*- encoding: utf-8 -*-
"""
Controller class for the 3d reservoir window

Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED

"""

import os
from datetime import datetime
from pymap3d import geodetic2ned
from PyQt4 import QtGui, uic
import numpy as np

ui_path = os.path.dirname(__file__)
FC_WINDOW_PATH = os.path.join(ui_path, 'views', 'reservoirwindow.ui')
Ui_ReservoirWindow = uic.loadUiType(FC_WINDOW_PATH)[0]

from PyQt4.QtGui import QWidget


class ReservoirWindow(QWidget):

    def __init__(self, core):
        super(ReservoirWindow, self).__init__()
        self.core = core

        # Setup the user interface
        self.ui = Ui_ReservoirWindow()
        self.ui.setupUi(self)
        self.ui.scaleSpinBox.valueChanged.connect(self.on_scaling_changed)

        core.project_loaded.connect(self.on_project_loaded)

    def clear_events(self):
        self.ui.viewerWidget.clear()

    def draw_catalog(self, show_all=True):
        if self.core.project is None:
            return
        scaling = self.ui.scaleSpinBox.value()
        t_max = datetime.max if show_all else self.core.project.project_time
        events = [e for e in self.core.project.seismic_catalog.seismic_events
                  if e.date_time < t_max]
        loc = np.array([(e.lat, e.lon, e.depth) for e in events])
        mag = np.array([e.magnitude for e in events]) * scaling

        ref = self.core.project.reference_point
        lat, lon, h = loc[:, 0], loc[:, 1], -loc[:, 2]
        n, e, d = geodetic2ned(lat, lon, h, ref['lat'], ref['lon'], ref['h'])
        self.ui.viewerWidget.show_events(np.array([n, e, d]).T, size=mag)

    def on_project_loaded(self, project):
        project.seismic_catalog.history_changed.connect(
            self.on_catalog_changed)

    def on_project_will_unload(self):
        self.clear_events()

    def on_catalog_changed(self, _):
        show_all = not self.ui.limitTimeCheckBox.isChecked()
        self.draw_catalog(show_all=show_all)

    def on_scaling_changed(self):
        show_all = not self.ui.limitTimeCheckBox.isChecked()
        self.draw_catalog(show_all=show_all)