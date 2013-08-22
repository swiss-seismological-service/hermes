# -*- encoding: utf-8 -*-
"""
Additions for PyQtGraph

Atlas specific classes used in various places of the user interface
    
"""

import pyqtgraph as pg
from datetime import time, datetime, timedelta


class DateAxis(pg.AxisItem):
    """An AxisItem that displays dates

    The display format is adjusted automatically depending on the date range
    given in values.

    :param values: time values (seconds in epoch)

    """
    def tickStrings(self, values, scale, spacing):
        # FIXME: Implement this properly some time
        epoch = datetime(1970, 1, 1)
        dates = [epoch + timedelta(seconds=v) for v in values]
        strns = []
        rng = max(values) - min(values)
        #if rng < 120:
        #    return pg.AxisItem.tickStrings(self, values, scale, spacing)
        if rng < 3600*24:
            string = '%H:%M:%S'
        elif rng >= 3600*24 and rng < 3600*24*30:
            string = '%d'
        elif rng >= 3600*24*30 and rng < 3600*24*30*24:
            string = '%b'
        elif rng >=3600*24*30*24:
            string = '%Y'
        for x in dates:
            try:
                strns.append(x.strftime(string))
            except ValueError:  # Windows can't handle dates before 1970
                strns.append('')

        return strns



class TimePlotWidget(pg.PlotWidget):
    """ A plot widget where the x-Axis is a DateAxis"""

    def __init__(self, parent=None, **kargs):
        axis = DateAxis(orientation='bottom')
        super(TimePlotWidget, self).__init__(parent, axisItems={'bottom': axis},
                                             **kargs)


class SeismicityPlotWidget(TimePlotWidget):
    """pyqtgraph PlotWidget configured to display seismic data

    :ivar plot: :class:`ScatterPlotItem` that holds the scatter plot data

    """

    def __init__(self, parent=None, **kargs):
        super(SeismicityPlotWidget, self).__init__(parent, **kargs)
        self.plot = pg.ScatterPlotItem(size=5, pen=pg.mkPen(None),
                                       brush=pg.mkBrush(255, 255, 255, 120))
        self.addItem(self.plot)