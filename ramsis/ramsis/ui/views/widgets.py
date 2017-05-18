# -*- encoding: utf-8 -*-
"""
Custom QtWidgets for plotting
   
"""

import pyqtgraph as pg
import pyqtgraph.opengl as gl
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure
import numpy as np
from datetime import datetime
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


class CurvePlotWidget(pg.PlotWidget):

    def __init__(self, parent=None, **kargs):
        super(CurvePlotWidget, self).__init__(parent, **kargs)
        self.getPlotItem().setLogMode(y=True)
        self.setMouseEnabled(y=False)


class TimePlotWidget(pg.PlotWidget):
    """ A plot widget where the x-Axis is a DateAxis """

    def __init__(self, parent=None, **kargs):
        axis = pg.DateAxisItem(orientation='bottom')
        super(TimePlotWidget, self).__init__(parent,
                                             axisItems={'bottom': axis},
                                             **kargs)

        self.setMouseEnabled(y=False)
        self._range = DisplayRange.DEFAULT

        # Current time indicator (vertical line)
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen='g')
        self.addItem(self.v_line)

        self.sigRangeChanged.connect(self.on_axis_range_changed)

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

    def on_axis_range_changed(self):
        self.getAxis('bottom').setLabel('Time', self.get_bottom_axis_units())

    def get_bottom_axis_units(self):
        xmin, xmax = [datetime.utcfromtimestamp(v - time.timezone)
                          for v in self.viewRange()[0]]
        if xmin.year != xmax.year:
            return ''
        if xmin.month != xmax.month:
            return xmin.strftime('%Y')
        if xmin.day != xmax.day:
            return xmin.strftime('%B %Y')
        if xmin.minute != xmax.minute:
            return xmin.strftime('%d %B %Y').lstrip('0')
        return xmin.strftime('%d %B %Y, %H:%M').lstrip('0')


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
        self.getAxis('left').enableAutoSIPrefix(False)
        self.getAxis('bottom').enableAutoSIPrefix(False)
        self.getAxis('left').setLabel('Mag', 'Mw')


class TimeLinePlotWidget(TimePlotWidget):
    """
    pyqtgraph PlotWidget configured to display seismic data

    :ivar plot: :class:`ScatterPlotItem` that holds the scatter plot data

    """

    def __init__(self, parent=None, **kargs):
        super(TimeLinePlotWidget, self).__init__(parent, **kargs)
        self.plot = pg.ScatterPlotItem(size=5, pen=pg.mkPen(None),
                                       brush=pg.mkBrush(255, 255, 255, 120))

        self.symbol_view = pg.ViewBox()
        self.plotItem.scene().addItem(self.symbol_view)
        self.symbol_view.setXLink(self.plotItem)
        self.symbol_view.setRange(yRange=(0, 1))
        self.symbol_view.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
        fc_brush = pg.mkBrush(0, 255, 0, 255)
        self.forecasts_plot = pg.ScatterPlotItem(pen=pg.mkPen(None),
                                                 symbol='t',
                                                 brush=fc_brush)
        self.addItem(self.plot)
        self.symbol_view.addItem(self.forecasts_plot)
        self.getAxis('left').enableAutoSIPrefix(False)
        self.getAxis('bottom').enableAutoSIPrefix(False)
        self.getAxis('left').setLabel('Mag', 'Mw')

        self.plotItem.vb.sigResized.connect(self._update_views)
        self._update_views()

    def _update_views(self):
        self.symbol_view.setGeometry(self.plotItem.vb.sceneBoundingRect())
        self.symbol_view.linkedViewChanged(self.plotItem.vb,
                                           self.symbol_view.XAxis)


class HydraulicsPlotWidget(TimePlotWidget):
    """
    pyqtgraph PlotWidget configured to display hydraulic data

    :ivar plot: :class:`PlotCurveItem` that holds the line plot data

    """
    def __init__(self, parent=None, **kargs):
        super(HydraulicsPlotWidget, self).__init__(parent, **kargs)
        self.plot = pg.PlotCurveItem()
        self.addItem(self.plot)
        self.getAxis('left').enableAutoSIPrefix(False)
        self.getAxis('bottom').enableAutoSIPrefix(False)
        self.getAxis('left').setLabel('Flow rate', 'l/s')


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
        self.getAxis('left').enableAutoSIPrefix(False)
        self.getAxis('bottom').enableAutoSIPrefix(False)
        self.getAxis('left').setLabel('Rate of Seismicity', '6h^(-1)')

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
        self.setCameraPosition(distance=1000)
        pos = np.array([0, 1.0])
        color = np.array([[  0,   0,   0,   0],
                          [  0, 255,   0, 150]], dtype=np.ubyte)
        self.color_map = pg.ColorMap(pos, color)

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
        x_grid.scale(40, 20, 20)
        y_grid.scale(40, 20, 20)
        z_grid.scale(20, 40, 20)

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

        # FIXME: this depends on the voxel length defined in MATLAB
        scale = 100.0
        voxels = self.color_map.map(data/np.amax(data).astype(np.float32))

        l = round(len(data)**(1/3.0))
        voxels = voxels.reshape((l,l,l,4), order='F')

        self._voxel_item = gl.GLVolumeItem(voxels, smooth=True, sliceDensity=10)
        t = -l / 2 * scale
        self._voxel_item.translate(t, t, t)
        self._voxel_item.scale(scale,scale,scale)
        self.addItem(self._voxel_item)


class Event3DViewWidget(gl.GLViewWidget):
    def __init__(self, parent=None, **kargs):
        super(Event3DViewWidget, self).__init__(parent, **kargs)
        self._grid_items = None
        self._events_item = None
        self.setWindowTitle('3D Event View')
        self._add_grid()
        self.setCameraPosition(distance=2000)


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
        x_grid.scale(40, 20, 20)
        y_grid.scale(40, 20, 20)
        z_grid.scale(20, 40, 20)

    def clear(self):
        if self._events_item is not None:
            self.removeItem(self._events_item)
            self._events_item = None

    def show_events(self, pos, size):
        """
        Show events

        :param pos: 3d array of event positions
        :param size: 1d array of event magnitudes

        """
        self.clear()
        self._events_item = gl.GLScatterPlotItem()
        self._events_item.setData(pos=pos, size=10*size)
        self.addItem(self._events_item)


class HCurveWidget(Canvas):
    """ Widget for hazard curves """
    def __init__(self, parent=None):
        self.figure = Figure()
        self.figure.patch.set_facecolor('none')
        self.figure.subplots_adjust(bottom=0.15)
        self.axes = self.figure.add_subplot(111)
        self._draw_labels()

        Canvas.__init__(self, self.figure)
        self.setParent(parent)

    def plot(self, *args, **kwargs):
        self.axes.plot(*args, **kwargs)
        self._draw_labels()
        self.draw()

    def _draw_labels(self):
        self.axes.set_xlabel('Magnitude')
        self.axes.set_ylabel('poE')