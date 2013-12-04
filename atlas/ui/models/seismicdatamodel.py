# -*- encoding: utf-8 -*-
"""
(GUI) Model for the seismic catalog

Serves up seismic catalog data for Qt
    
"""

from PyQt4 import QtCore


class SeismicDataModel(QtCore.QAbstractTableModel):
    """ Represents the seismic catalog in Qt

        :ivar _headers: column headers
        :type _headers: list
        :ivar seismic_history: seismic event history
        :type seismic_history: SeismicEventHistory

    """

    def __init__(self, event_history, parent=None):
        """Provides the seismic data catalog to the Qt user interface

        :param event_history: Event history
        :type event_history: SeismicEventHistory

        """
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._event_history = event_history
        self._headers = ('date', 'magnitude', 'lat', 'lon', 'depth')

    def rowCount(self, parent):
        num_rows = len(self._event_history)
        print 'num rows: ' + str(num_rows)
        return num_rows

    def columnCount(self, parent):
        return 5

    def flags(self, index):
        return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index, role):

        if role == QtCore.Qt.EditRole:
            row = index.row()
            column = index.column()
            pass


        if role == QtCore.Qt.ToolTipRole:
            row = index.row()
            pass


        if role == QtCore.Qt.DecorationRole:
            row = index.row()
            column = index.column()
            pass

        if role == QtCore.Qt.DisplayRole:
            row = index.row()
            column = index.column()
            event = self._event_history[row]
            print 'loading data for row ' + str(row) + ', column: ' + str(column)

            if column == 0:
                return str(event.date_time)
            elif column == 1:
                return str(event.magnitude)
            elif column == 2:
                return str(event.latitude)
            elif column == 3:
                return str(event.longitude)
            else:
                return str(event.depth)


    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """
        if role == QtCore.Qt.EditRole:

            row = index.row()
            column = index.column()

            color = QtGui.QColor(value)

            if color.isValid():
                self.__colors[row][column] = color
                self.dataChanged.emit(index, index)
                return True
        return False
        """
        pass




    def headerData(self, section, orientation, role):

        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:

                if section < len(self._headers):
                    return self._headers[section]
                else:
                    return "not implemented"
            else:
                return QtCore.QString("Event %1").arg(section)