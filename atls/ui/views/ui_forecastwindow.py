# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'forecastwindow.ui'
#
# Created: Fri Jun 13 13:38:37 2014
#      by: PyQt4 UI code generator 4.10.4
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
        ForecastWindow.resize(739, 595)
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
        self.voxel_plot = VoxelViewWidget(ForecastWindow)
        self.voxel_plot.setGeometry(QtCore.QRect(380, 300, 341, 281))
        self.voxel_plot.setObjectName(_fromUtf8("voxel_plot"))
        self.log_likelihood_label = QtGui.QLabel(ForecastWindow)
        self.log_likelihood_label.setGeometry(QtCore.QRect(180, 430, 191, 16))
        self.log_likelihood_label.setObjectName(_fromUtf8("log_likelihood_label"))
        self.label_3 = QtGui.QLabel(ForecastWindow)
        self.label_3.setGeometry(QtCore.QRect(10, 430, 101, 16))
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.fc_time_label = QtGui.QLabel(ForecastWindow)
        self.fc_time_label.setGeometry(QtCore.QRect(180, 330, 191, 16))
        self.fc_time_label.setObjectName(_fromUtf8("fc_time_label"))
        self.label = QtGui.QLabel(ForecastWindow)
        self.label.setGeometry(QtCore.QRect(10, 330, 101, 16))
        self.label.setObjectName(_fromUtf8("label"))
        self.pred_rate_label = QtGui.QLabel(ForecastWindow)
        self.pred_rate_label.setGeometry(QtCore.QRect(180, 350, 111, 16))
        self.pred_rate_label.setObjectName(_fromUtf8("pred_rate_label"))
        self.label_2 = QtGui.QLabel(ForecastWindow)
        self.label_2.setGeometry(QtCore.QRect(10, 350, 141, 16))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.label_4 = QtGui.QLabel(ForecastWindow)
        self.label_4.setGeometry(QtCore.QRect(10, 300, 141, 16))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_4.setFont(font)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.rating_time_label = QtGui.QLabel(ForecastWindow)
        self.rating_time_label.setGeometry(QtCore.QRect(180, 450, 191, 16))
        self.rating_time_label.setObjectName(_fromUtf8("rating_time_label"))
        self.label_5 = QtGui.QLabel(ForecastWindow)
        self.label_5.setGeometry(QtCore.QRect(10, 400, 141, 16))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_5.setFont(font)
        self.label_5.setObjectName(_fromUtf8("label_5"))

        self.retranslateUi(ForecastWindow)
        QtCore.QMetaObject.connectSlotsByName(ForecastWindow)

    def retranslateUi(self, ForecastWindow):
        ForecastWindow.setWindowTitle(_translate("ForecastWindow", "Rates and Forecasts", None))
        self.log_likelihood_label.setText(_translate("ForecastWindow", "-", None))
        self.label_3.setText(_translate("ForecastWindow", "Log Likelihood", None))
        self.fc_time_label.setText(_translate("ForecastWindow", "-", None))
        self.label.setText(_translate("ForecastWindow", "Forecast time", None))
        self.pred_rate_label.setText(_translate("ForecastWindow", "-", None))
        self.label_2.setText(_translate("ForecastWindow", "Predictated total rate", None))
        self.label_4.setText(_translate("ForecastWindow", "Forecast Results", None))
        self.rating_time_label.setText(_translate("ForecastWindow", "-", None))
        self.label_5.setText(_translate("ForecastWindow", "Model Performance", None))

from plots import VoxelViewWidget, RateForecastPlotWidget
