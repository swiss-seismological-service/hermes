# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'simulationcontrolwindow.ui'
#
# Created: Mon Jan 13 09:25:07 2014
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

class Ui_SimulationControlWindow(object):
    def setupUi(self, SimulationControlWindow):
        SimulationControlWindow.setObjectName(_fromUtf8("SimulationControlWindow"))
        SimulationControlWindow.resize(400, 244)
        self.controlsBox = QtGui.QGroupBox(SimulationControlWindow)
        self.controlsBox.setEnabled(True)
        self.controlsBox.setGeometry(QtCore.QRect(10, 0, 371, 121))
        self.controlsBox.setObjectName(_fromUtf8("controlsBox"))
        self.simulationCheckBox = QtGui.QCheckBox(self.controlsBox)
        self.simulationCheckBox.setGeometry(QtCore.QRect(20, 80, 131, 20))
        self.simulationCheckBox.setChecked(True)
        self.simulationCheckBox.setObjectName(_fromUtf8("simulationCheckBox"))
        self.startButton = QtGui.QPushButton(self.controlsBox)
        self.startButton.setGeometry(QtCore.QRect(10, 30, 111, 32))
        self.startButton.setObjectName(_fromUtf8("startButton"))
        self.pauseButton = QtGui.QPushButton(self.controlsBox)
        self.pauseButton.setGeometry(QtCore.QRect(120, 30, 111, 32))
        self.pauseButton.setObjectName(_fromUtf8("pauseButton"))
        self.stopButton = QtGui.QPushButton(self.controlsBox)
        self.stopButton.setGeometry(QtCore.QRect(230, 30, 111, 32))
        self.stopButton.setObjectName(_fromUtf8("stopButton"))
        self.speedBox = QtGui.QSpinBox(self.controlsBox)
        self.speedBox.setGeometry(QtCore.QRect(260, 77, 71, 25))
        self.speedBox.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.speedBox.setMinimum(1)
        self.speedBox.setMaximum(10000)
        self.speedBox.setProperty("value", 1000)
        self.speedBox.setObjectName(_fromUtf8("speedBox"))
        self.speedLabel = QtGui.QLabel(self.controlsBox)
        self.speedLabel.setGeometry(QtCore.QRect(204, 80, 51, 20))
        self.speedLabel.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.speedLabel.setObjectName(_fromUtf8("speedLabel"))
        self.groupBox = QtGui.QGroupBox(SimulationControlWindow)
        self.groupBox.setGeometry(QtCore.QRect(10, 130, 371, 101))
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.simulationCheckBox_2 = QtGui.QCheckBox(self.groupBox)
        self.simulationCheckBox_2.setGeometry(QtCore.QRect(20, 30, 221, 20))
        self.simulationCheckBox_2.setChecked(True)
        self.simulationCheckBox_2.setObjectName(_fromUtf8("simulationCheckBox_2"))
        self.label = QtGui.QLabel(self.groupBox)
        self.label.setGeometry(QtCore.QRect(160, 65, 201, 20))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setObjectName(_fromUtf8("label"))
        self.pushButton = QtGui.QPushButton(self.groupBox)
        self.pushButton.setGeometry(QtCore.QRect(10, 60, 141, 32))
        self.pushButton.setObjectName(_fromUtf8("pushButton"))

        self.retranslateUi(SimulationControlWindow)
        QtCore.QMetaObject.connectSlotsByName(SimulationControlWindow)

    def retranslateUi(self, SimulationControlWindow):
        SimulationControlWindow.setWindowTitle(_translate("SimulationControlWindow", "Dialog", None))
        self.controlsBox.setTitle(_translate("SimulationControlWindow", "Simulation", None))
        self.simulationCheckBox.setText(_translate("SimulationControlWindow", "As fast as possible", None))
        self.startButton.setText(_translate("SimulationControlWindow", "Start", None))
        self.pauseButton.setText(_translate("SimulationControlWindow", "Pause", None))
        self.stopButton.setText(_translate("SimulationControlWindow", "Stop", None))
        self.speedBox.setSuffix(_translate("SimulationControlWindow", "x", None))
        self.speedLabel.setText(_translate("SimulationControlWindow", "Speed", None))
        self.groupBox.setTitle(_translate("SimulationControlWindow", "Run Output", None))
        self.simulationCheckBox_2.setText(_translate("SimulationControlWindow", "Write simulation results to file", None))
        self.label.setText(_translate("SimulationControlWindow", "~/Desktop/AtlasResults", None))
        self.pushButton.setText(_translate("SimulationControlWindow", "Output Directory...", None))

