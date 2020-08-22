# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Time line presenter controlling facilities.
"""

import logging

from datetime import datetime
from operator import attrgetter

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QStyleFactory

import pyqtgraph as pg

log = logging.getLogger(__name__)

DATETIME_POSIX_START = datetime(1970, 1, 1)


class TimeLinePresenter(QObject):
    """
    A base class for presenting time lines

    """

    def __init__(self, ui, core):
        super().__init__()
        self.ui = ui
        self.core = core
        self.displayed_time = DATETIME_POSIX_START

        # configure time line widget (use time_line as shortcut)
        self.time_line = self.ui.timeLineWidget
        self.time_line.setBackground(None)
        self.time_line.getAxis('bottom').setPen('w')
        self.time_line.getAxis('left').setPen('w')

        # timeline selector
        self.sel = self.ui.timelineSelectionBox
        self.sel.setStyle(
            QStyleFactory.create('Plastique'))
        self.sel.insertItems(0, ('Seismicity', 'Injection'))
        self.sel.currentIndexChanged.connect(self.on_timeline_selection)
        self.plotter = SeismicityPlotter(self.time_line)

        core.project_loaded.connect(self.on_project_loaded)
        core.project_data_changed.connect(self.on_project_data_changed)
        core.clock.time_changed.connect(self.on_time_changed)

        if core.project:
            self.present_time_line_for_project(core.project)
        else:
            end = (datetime.utcnow() - DATETIME_POSIX_START).total_seconds()
            start = end - 2 * 356 * 24 * 3600
            self.time_line.setRange(xRange=(start, end))

    def present_time_line_for_project(self, project):
        """
        Show the events of project in the timeline

        :param project: Current project
        :type project: :py:class:`ramsis.datamodel.project.Project`

        """
        if project is None:
            return

        try:
            start_time = min(project.forecast_iter(),
                             key=attrgetter('starttime')).starttime
        except ValueError:
            start_time = project.starttime

        start = (start_time - DATETIME_POSIX_START).total_seconds()
        # TODO(damb): Set endtime to either project endtime or latest forecast
        # endtime
        end_time = project.endtime or datetime.utcnow()
        end = (end_time - DATETIME_POSIX_START).total_seconds()
        self.time_line.setRange(xRange=(start, end))
        self.replot()
        self.show_current_time(self.core.clock.time)

    def show_current_time(self, t):
        dt = (t - self.displayed_time).total_seconds()
        self.displayed_time = t
        # we do a more efficient relative change if the change is not too big
        if abs(dt) > self.ui.timeLineWidget.display_range:
            pos = (t - DATETIME_POSIX_START).total_seconds()
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
        self.plotter.replot(self.core.project, max_time=max_time)

    def show_forecasts(self):
        if self.core.project is None:
            self.time_line.forecasts_plot.setData(None)
            return
        # TODO LH: since we display time as total seconds since Epoch we might
        #   as well have a utility function that gives us that. We could use
        #   datetime.timestamp() with python3 but it doesn't work with naive
        #   datetimes that represent UTC (which is what we have). We could
        #   also make sure that the datamodel always returns aware datetimes
        #   with UTC set explicitly.
        forecasts = self.core.project.forecasts
        data = [((f.starttime - DATETIME_POSIX_START).total_seconds(), 1.0)
                for f in forecasts]
        self.time_line.forecasts_plot.setData(pos=data)

    # signal slots

    def on_project_loaded(self, project):
        # TODO LH: observe project catalog, forecasts and settings which no
        #   longer emit change signals.
        self.present_time_line_for_project(project)
        self.replot()
        self.show_forecasts()

    def on_project_will_close(self):
        self.present_time_line_for_project(None)

    def on_time_changed(self, current_time):
        self.show_current_time(current_time)

    def on_project_data_changed(self, obj):
        # TODO LH: this is obv. a bit ugly, see controller signals
        if obj == self.core.project.forecasts:
            self.show_forecasts()
        elif obj == self.core.project.seismiccatalog:
            self.replot()
        elif obj == self.core.project.settings:
            self.present_time_line_for_project(self.core.project)

    def on_timeline_selection(self, index):
        if index == 0:
            self.plotter = SeismicityPlotter(self.time_line)
        else:
            self.plotter = InjectionPlotter(self.time_line)
        self.replot()


class SeismicityPlotter(object):
    """ Plots the seismicity timeline on *plot* """
    def __init__(self, widget):
        self.widget = widget
        self.project = None
        plot = pg.ScatterPlotItem(size=5, pen=pg.mkPen(None),
                                  brush=pg.mkBrush(255, 255, 255, 120))
        self.widget.set_plot(plot, ('Mag', 'Mw'))

    def replot(self, project=None, max_time=None):
        epoch = DATETIME_POSIX_START
        if project and project.seismiccatalog:
            events = project.seismiccatalog.events
            if max_time:
                data = [((e.datetime_value - epoch).total_seconds(),
                         e.magnitude_value)
                        for e in events if e.date_time < max_time]
            else:
                data = [((e.datetime_value - epoch).total_seconds(),
                         e.magnitude_value)
                        for e in events]
        else:
            data = []
        x, y = list(map(list, list(zip(*data)))) if len(data) > 0 else ([], [])
        self.widget.setYRange(min(y) if y else 0, max(y) if y else 4)
        self.widget.plot.setData(x, y)


class InjectionPlotter(object):
    """ Plots the injection timeline on *plot* """
    def __init__(self, widget):
        self.widget = widget
        self.project = None
        plot = pg.PlotCurveItem()
        self.widget.set_plot(plot, ('Flow', 'm^3/s'))

    def replot(self, project=None, max_time=None):
        epoch = DATETIME_POSIX_START
        if project:
            try:
                hydraulics = project.wells[0].sections[0].hydraulics
            except (TypeError, AttributeError):
                hydraulics = []

            if max_time:
                data = [((s.datetime_value - epoch).total_seconds(),
                         s.topflow_value)
                        for s in hydraulics if s.datetime_value < max_time]
            else:
                data = [((s.datetime_value - epoch).total_seconds(),
                         s.topflow_value) for s in hydraulics]
        else:
            data = []

        x, y = list(map(list, list(zip(*data)))) if len(data) > 0 else ([], [])
        self.widget.setYRange(min(y) if y else 0, max(y) if y else 100)
        self.widget.plot.setData(x, y)
