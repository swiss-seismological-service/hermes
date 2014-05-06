# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'forecastwindow.ui'
#
# Created: Thu Dec 12 15:47:25 2013
#      by: PyQt4 UI code generator 4.10.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_ForecastWindow(object):
    def setupUi(self, ForecastWindow):
        ForecastWindow.setObjectName(_fromUtf8("ForecastWindow"))
        ForecastWindow.resize(735, 290)
        self.frame = QtGui.QFrame(ForecastWindow)
        self.frame.setGeometry(QtCore.QRect(10, 40, 711, 231))
        self.frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.frame.setObjectName(_fromUtf8("frame"))
        self.rate_forecast_plot = RateForecastPlotWidget(self.frame)
        self.rate_forecast_plot.setGeometry(QtCore.QRect(-1, -1, 711, 231))
        self.rate_forecast_plot.setObjectName(_fromUtf8("rate_forecast_plot"))
        self.modelSelectorComboBox = QtGui.QComboBox(ForecastWindow)
        self.modelSelectorComboBox.setGeometry(QtCore.QRect(543, 10, 181, 26))
        self.modelSelectorComboBox.setObjectName(_fromUtf8("modelSelectorComboBox"))

        self.retranslateUi(ForecastWindow)
        QtCore.QMetaObject.connectSlotsByName(ForecastWindow)

    def retranslateUi(self, ForecastWindow):
        ForecastWindow.setWindowTitle(_translate("ForecastWindow", "Rates and Forecasts", None))

from plots import RateForecastPlotWidget
