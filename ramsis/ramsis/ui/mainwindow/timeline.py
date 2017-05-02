# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2015, SED (ETH Zurich)

"""
import logging
from datetime import datetime, timedelta
from PyQt4 import QtCore

log = logging.getLogger(__name__)


class TimeLinePresenter(QtCore.QObject):
    """
    A base class for presenting time lines

    """
    def __init__(self, ui, core):
        super(TimeLinePresenter, self).__init__()
        self.ui = ui
        self.core = core
        self.displayed_project_time = datetime(1970, 1, 1)

        # configure time line widget (use time_line as shortcut)
        self.time_line = self.ui.timeLineWidget
        self.time_line.setBackground(None)
        self.time_line.getAxis('bottom').setPen('w')
        self.time_line.getAxis('left').setPen('w')

        core.project_loaded.connect(self.on_project_loaded)

        if core.project:
            self.present_time_line_for_project(core.project)
        else:
            end = (datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()
            start = end - 2 * 356 * 24 * 3600
            self.time_line.setRange(xRange=(start, end))

    def present_time_line_for_project(self, project):
        """
        Show the events of project in the timeline

        :param Project project: current project

        """
        if project is None:
            return
        start = (project.start_date - datetime(1970, 1, 1)).total_seconds()
        end = (project.end_date - datetime(1970, 1, 1)).total_seconds()
        self.time_line.setRange(xRange=(start, end))
        self.replot()
        self.show_current_time(project.project_time)

    def show_current_time(self, t):
        dt = (t - self.displayed_project_time).total_seconds()
        self.displayed_project_time = t
        # we do a more efficient relative change if the change is not too big
        if abs(dt) > self.ui.timeLineWidget.display_range:
            epoch = datetime(1970, 1, 1)
            pos = (t - epoch).total_seconds()
            self.time_line.marker_pos = pos
        else:
            self.time_line.advance_time(dt)

    def zoom(self, display_range):
        self.time_line.zoom(display_range=display_range)

    def replot(self, max_time=None):
        """
        Plot the data in the time line

        :param max_time: if not None, plot up to max_time only

        """
        epoch = datetime(1970, 1, 1)
        events = self.core.project.seismic_catalog.seismic_events
        if max_time:
            data = [((e.date_time - epoch).total_seconds(), e.magnitude)
                    for e in events if e.date_time < max_time]
        else:
            data = [((e.date_time - epoch).total_seconds(), e.magnitude)
                    for e in events]
        self.time_line.plot.setData(pos=data)

    def show_forecasts(self):
        if self.core.project is None:
            self.time_line.forecasts_plot.setData(None)
            return
        epoch = datetime(1970, 1, 1)
        forecasts = self.core.project.forecast_set.forecasts
        data = [((f.forecast_time - epoch).total_seconds(), 1.0)
                for f in forecasts]
        self.time_line.forecasts_plot.setData(pos=data)

    # signal slots

    def on_project_loaded(self, project):
        project.will_close.connect(self.on_project_will_close)
        project.project_time_changed.connect(self.on_project_time_changed)
        project.settings.settings_changed.connect(self.on_settings_changed)
        project.seismic_catalog.history_changed.connect(
            self.on_catalog_changed)
        project.forecast_set.forecasts_changed.connect(
            self.on_forecasts_changed)
        self.present_time_line_for_project(project)
        self.replot()
        self.show_forecasts()

    def on_project_will_close(self, project):
        self.present_time_line_for_project(None)

    def on_project_time_changed(self, project_time):
        self.show_current_time(project_time)

    def on_forecasts_changed(self, _):
        self.show_forecasts()

    def on_settings_changed(self, settings):
        self.present_time_line_for_project(self.core.project)

    def on_catalog_changed(self, _):
        self.replot()
