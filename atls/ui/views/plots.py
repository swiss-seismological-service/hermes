# -*- encoding: utf-8 -*-
"""
Additions for PyQtGraph

Atls specific classes used in various places of the user interface
    
"""

import pyqtgraph as pg
import pyqtgraph.opengl as gl
import numpy as np
import logging
from collections import namedtuple
from datetime import datetime, timedelta
import time


CUR_FC_BRUSH = (205, 72, 66, 100)
CUR_FC_PEN = (205, 72, 66, 150)
PAST_FC_BRUSH = (200, 200, 200, 100)
PAST_FC_PEN = (80, 80, 80, 255)


class DisplayRange(object):
    DAY = 24*3600
    WEEK = 7*24*3600
    MONTH = 30*7*24*3600
    DEFAULT = WEEK


class DateTickFormat(object):

    TickSpec = namedtuple('TickSpec', ['spacing', 'format'])

    SECOND_SPACING = 1
    MINUTE_SPACING = 60
    HOUR_SPACING = 3600
    DAY_SPACING = 24 * HOUR_SPACING
    WEEK_SPACING = 7 * DAY_SPACING
    MONTH_SPACING = 30 * DAY_SPACING
    YEAR_SPACING = 365 * DAY_SPACING

    def __init__(self, tick_specs=None):
        """
        The tick_specs define the specification for each tick level in
        descending order (major, minor, ...), where *spacing* holds the
        (approximate) spacing for the tick level and *format* a strftime
        compatible format string from which the tick label will be generated.
        Note that major ticks replace minor ticks where they have the same
        location.

        :param tick_specs: List of TickSpec objects
        """
        super(DateTickFormat, self).__init__()
        self.tick_specs = tick_specs if tick_specs else []
        self.utc_offset = 0

    def tick_values(self, minVal, maxVal):
        all_ticks = []
        value_specs = []
        for spec in self.tick_specs:
            spc = spec.spacing
            if spc == DateTickFormat.MONTH_SPACING:
                ticks = self._month_ticks(minVal, maxVal, self.utc_offset)
            elif spc == DateTickFormat.YEAR_SPACING:
                ticks = self._year_ticks(minVal, maxVal, self.utc_offset)
            else:
                first = int(minVal / spc + 1) * spc + self.utc_offset
                last = int(maxVal / spc) * spc + self.utc_offset
                ticks = np.linspace(first, last, (last-first)/spc+1).tolist()
            # remove any ticks that were present in higher levels
            ticks = [x for x in ticks if x not in all_ticks]
            all_ticks.extend(ticks)
            value_specs.append((spc, ticks))
        return value_specs

    def _year_ticks(self, minVal, maxVal, offset):
        """
        Returns the time stamp of Jan 1 of each year within the range given
        by minVal, maxVal

        """
        epoch = datetime(1970, 1, 1)
        ticks = []
        min_date = datetime.fromtimestamp(minVal)
        date = datetime(min_date.year + 1, 1, 1) + timedelta(seconds=offset)
        while date < datetime.fromtimestamp(maxVal):
            ticks.append((date - epoch).total_seconds())
            date = datetime(date.year + 1, 1, 1) + timedelta(seconds=offset)
        return ticks

    def _month_ticks(self, minVal, maxVal, offset):
            """
            Returns the time stamp of the 1st of each month within the range
            given by minVal, maxVal

            """
            def _next_month(date):
                dy = date.month / 12
                date -= timedelta(seconds=offset)
                date = datetime(date.year + dy, (date.month) % 12 + 1, 1)
                date += timedelta(seconds=offset)
                return date

            epoch = datetime(1970, 1, 1)
            ticks = []
            min_date = datetime.fromtimestamp(minVal)
            date = _next_month(min_date)
            while date < datetime.fromtimestamp(maxVal):
                ticks.append((date - epoch).total_seconds())
                date = _next_month(date)
            return ticks

    def __repr__(self):
        return '<Spacings: {}>'.format([s.spacing for s in self.tick_specs])



class DateAxis(pg.AxisItem):
    """
    An AxisItem that displays dates

    The display format is adjusted automatically depending on the date range
    given in values.

    :param values: time values (seconds in epoch)

    """

    YEAR_MONTH_TICK_FORMAT = DateTickFormat([
        DateTickFormat.TickSpec(DateTickFormat.YEAR_SPACING, '%Y'),
        DateTickFormat.TickSpec(DateTickFormat.MONTH_SPACING, '%b')
    ])
    MONTH_DAY_TICK_FORMAT = DateTickFormat([
        DateTickFormat.TickSpec(DateTickFormat.MONTH_SPACING, '%b %d'),
        DateTickFormat.TickSpec(DateTickFormat.DAY_SPACING, '%d')
    ])
    DAY_6HOUR_TICK_FORMAT = DateTickFormat([
        DateTickFormat.TickSpec(DateTickFormat.DAY_SPACING, '%a %d'),
        DateTickFormat.TickSpec(6*DateTickFormat.HOUR_SPACING, '%H:%M')
    ])
    DAY_HOUR_TICK_FORMAT = DateTickFormat([
        DateTickFormat.TickSpec(DateTickFormat.DAY_SPACING, '%a %d'),
        DateTickFormat.TickSpec(DateTickFormat.HOUR_SPACING, '%H:%M')
    ])

    def __init__(self, orientation, **kvargs):
        super(DateAxis, self).__init__(orientation, **kvargs)
        self.current_tick_format = DateAxis.YEAR_MONTH_TICK_FORMAT
        self._logger = logging.getLogger(__name__)

    def tickStrings(self, values, scale, spacing):
        tick_specs = self.current_tick_format.tick_specs
        tick_spec = next((x for x in tick_specs if x.spacing == spacing), None)
        if tick_spec is None:
            self._logger.error('No spec for spacing {} found in {}'.\
                               format(spacing, self.current_tick_format))
        dates = [datetime.fromtimestamp(v) for v in values]
        format_strings = []
        for x in dates:
            try:
                format_strings.append(x.strftime(tick_spec.format))
            except ValueError:  # Windows can't handle dates before 1970
                format_strings.append('')
        self._logger.debug('spacing: {} values: {} format: {}'.\
                           format(spacing, values,format_strings))
        return format_strings

    def tickValues(self, minVal, maxVal, size):
        self._set_tick_format_with_range(minVal, maxVal)
        values = self.current_tick_format.tick_values(minVal, maxVal)
        self._logger.debug('values within ({}, {}): {}'.\
            format(minVal, maxVal, values))
        return values

    def _set_tick_format_with_range(self, minVal, maxVal):
        """
        Returns the best tick format for a given timestamp range

        :param minVal: smallest time stamp to display
        :param maxVal: largest time stamp to display
        :return: DateTickFormat object

        """
        rng = maxVal - minVal
        if rng < 3600*6:
            format = DateAxis.DAY_HOUR_TICK_FORMAT
        elif rng < 3600*24*2:
            format = DateAxis.DAY_6HOUR_TICK_FORMAT
        elif rng < 3600*24*30:
            format = DateAxis.MONTH_DAY_TICK_FORMAT
        elif rng < 3600*24*30*24:
            format = DateAxis.YEAR_MONTH_TICK_FORMAT
        else:
            format = DateAxis.YEAR_MONTH_TICK_FORMAT
        format.utc_offset = time.timezone
        self.current_tick_format = format
        self._logger.debug('Set tick format {}'.format(format))


class TimePlotWidget(pg.PlotWidget):
    """ A plot widget where the x-Axis is a DateAxis """

    def __init__(self, parent=None, **kargs):
        axis = DateAxis(orientation='bottom')
        super(TimePlotWidget, self).__init__(parent, axisItems={'bottom': axis},
                                             **kargs)

        self.setMouseEnabled(y=False)
        self._range = DisplayRange.DEFAULT

        # Current time indicator (vertical line)
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen='g')
        self.addItem(self.v_line)

    @property
    def marker_pos(self):
        return self.v_line.value()

    @marker_pos.setter
    def marker_pos(self, t):
        self.v_line.setValue(t)

    @property
    def display_range(self):
        return self._range

    def advance_time(self, dt, translate=False):
        """
        Advances the plot marker by dt and translates the view range if
        necessary.

        """
        self.marker_pos = self.marker_pos + dt
        if translate:
            vb = self.plot.getViewBox()
            vb.translateBy((dt, 0))

    def zoom_to_marker(self):
        t_marker = self.marker_pos
        self.zoom(pos=t_marker)

    def zoom(self, pos=None, display_range=None):
        """
        Zooms to position *pos* with zoom level *zoom*. If either parameter is
        not specified, the current value for that parameter will be used

        :param pos: Position to zoom to
        :type pos: float
        :param display_range: Zoom level
        :type display_range: DisplayRange

        """
        vb = self.plotItem.getViewBox()
        if pos is None:
            pos = vb.viewRange()[0][0]
        if display_range is None:
            display_range = self.display_range
        else:
            self._range = display_range

        vb.setXRange(pos, pos + display_range)


class SeismicityPlotWidget(TimePlotWidget):
    """
    pyqtgraph PlotWidget configured to display seismic data

    :ivar plot: :class:`ScatterPlotItem` that holds the scatter plot data

    """

    def __init__(self, parent=None, **kargs):
        super(SeismicityPlotWidget, self).__init__(parent, **kargs)
        self.plot = pg.ScatterPlotItem(size=5, pen=pg.mkPen(None),
                                       brush=pg.mkBrush(255, 255, 255, 120))
        self.addItem(self.plot)


class HydraulicsPlotWidget(TimePlotWidget):
    """
    pyqtgraph PlotWidget configured to display hydraulic data

    :ivar plot: :class:`PlotCurveItem` that holds the line plot data

    """
    def __init__(self, parent=None, **kargs):
        super(HydraulicsPlotWidget, self).__init__(parent, **kargs)
        self.plot = pg.PlotCurveItem()
        self.addItem(self.plot)


class RateForecastPlotWidget(TimePlotWidget):
    """
    pyqtgraph PlotWidget configured to display forecasted and actual seismicity
    rates.

    :ivar forecast_plot: Bar graph of forecasted _rates
    :ivar rate_plot: Actual _rates plot

    """
    def __init__(self, parent=None, **kargs):
        super(RateForecastPlotWidget, self).__init__(parent, **kargs)
        self.rate_plot = pg.PlotCurveItem()
        self.addItem(self.rate_plot)
        self.forecast_bars = []

    def set_forecast_data(self, x, y):
        # FIXME: this looks like a bug in bargraphitem (the fact that it doesn't
        # allow initialization without data
        for bar in self.forecast_bars:
            self.removeItem(bar)
        self.forecast_bars = []
        if x is None or y is None:
            return
        xy = sorted(zip(x, y))
        for (bx, by) in xy:
            brush = CUR_FC_BRUSH if bx == xy[-1][0] else PAST_FC_BRUSH
            pen = CUR_FC_PEN if bx == xy[-1][0] else PAST_FC_PEN
            bar = pg.BarGraphItem(x0=[bx], height=[by], width=3600*6,
                                  brush=brush, pen=pen)
            self.forecast_bars.append(bar)
            self.addItem(bar)


class VoxelViewWidget(gl.GLViewWidget):
    def __init__(self, parent=None, **kargs):
        super(VoxelViewWidget, self).__init__(parent, **kargs)
        self._grid_items = None
        self._voxel_item = None
        self._add_grid()
        self.set_voxel_data(np.array([0,1,2,3,4,5,6,7]))

    def _add_grid(self):
        ## create three grids, add each to the view
        x_grid = gl.GLGridItem()
        y_grid = gl.GLGridItem()
        z_grid = gl.GLGridItem()
        self.addItem(x_grid)
        self.addItem(y_grid)
        self.addItem(z_grid)
        self._grid_items = [x_grid, y_grid, z_grid]

        ## rotate x and y grids to face the correct direction
        x_grid.rotate(90, 0, 1, 0)
        y_grid.rotate(90, 1, 0, 0)

        ## scale each grid differently
        x_grid.scale(0.4, 0.2, 0.2)
        y_grid.scale(0.4, 0.2, 0.2)
        z_grid.scale(0.2, 0.4, 0.2)

    def set_voxel_data(self, data):
        """

        :param data: voxel data or None
        :type data: numpy.ndarray

        """
        if self._voxel_item is not None:
            self.removeItem(self._voxel_item)
            self._voxel_item = None
        if data is None:
            return

        pos = np.array([0, 1.0])
        color = np.array([[  0,   0,   0,   0],
                          [  0, 255,   0, 255]], dtype=np.ubyte)
        map = pg.ColorMap(pos, color)
        voxels = map.map(data/np.amax(data).astype(np.float32))

        l = round(len(data)**(1/3.0))
        voxels = voxels.reshape((l,l,l,4))

        self._voxel_item = gl.GLVolumeItem(voxels, smooth=True, sliceDensity=10)
        self._voxel_item.translate(-l/2,-l/2,-l/2)
        self.addItem(self._voxel_item)
