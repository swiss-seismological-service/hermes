# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Controller class for the 3d reservoir window.

"""

from datetime import datetime
import numpy as np

from PyQt5.QtWidgets import QWidget

from RAMSIS.ui.utils import UiForm


class ReservoirWindow(QWidget, UiForm('reservoirwindow.ui')):

    def __init__(self, core):
        super().__init__()
        self.core = core

        self.ui.scaleSpinBox.valueChanged.connect(self.on_scaling_changed)

        core.project_loaded.connect(self.on_project_loaded)

    def clear_events(self):
        self.ui.viewerWidget.clear()

    def draw_catalog(self, show_all=True):
        if self.core.project is None:
            return
        scaling = self.ui.scaleSpinBox.value()
        t_max = datetime.max if show_all else self.core.clock.time
        events = [e for e in self.core.project.seismiccatalog
                  if e.datetime_value < t_max]
        loc = np.array([(e.x_value, e.y_value, e.z_value)
                        for e in events])
        mag = np.array([e.magnitude_value for e in events]) * scaling
        self.ui.viewerWidget.show_events(np.array(loc), size=mag)

    def on_project_loaded(self, project):
        project.seismiccatalog.history_changed.connect(
            self.on_catalog_changed)

    def on_project_will_unload(self):
        self.clear_events()

    def on_catalog_changed(self, _):
        show_all = not self.ui.limitTimeCheckBox.isChecked()
        self.draw_catalog(show_all=show_all)

    def on_scaling_changed(self):
        show_all = not self.ui.limitTimeCheckBox.isChecked()
        self.draw_catalog(show_all=show_all)
