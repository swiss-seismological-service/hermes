# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created: Tue Sep 24 11:45:01 2013
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

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(877, 463)
        self.centralWidget = QtGui.QWidget(MainWindow)
        self.centralWidget.setObjectName(_fromUtf8("centralWidget"))
        self.label = QtGui.QLabel(self.centralWidget)
        self.label.setGeometry(QtCore.QRect(10, 30, 141, 16))
        self.label.setObjectName(_fromUtf8("label"))
        self.frame = QtGui.QFrame(self.centralWidget)
        self.frame.setGeometry(QtCore.QRect(10, 60, 851, 151))
        self.frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.frame.setObjectName(_fromUtf8("frame"))
        self.catalog_plot = SeismicityPlotWidget(self.frame)
        self.catalog_plot.setGeometry(QtCore.QRect(-1, -1, 851, 151))
        self.catalog_plot.setObjectName(_fromUtf8("catalog_plot"))
        self.controlsBox = QtGui.QGroupBox(self.centralWidget)
        self.controlsBox.setEnabled(True)
        self.controlsBox.setGeometry(QtCore.QRect(10, 290, 291, 111))
        self.controlsBox.setObjectName(_fromUtf8("controlsBox"))
        self.simulationCheckBox = QtGui.QCheckBox(self.controlsBox)
        self.simulationCheckBox.setGeometry(QtCore.QRect(15, 80, 87, 20))
        self.simulationCheckBox.setChecked(True)
        self.simulationCheckBox.setObjectName(_fromUtf8("simulationCheckBox"))
        self.startButton = QtGui.QPushButton(self.controlsBox)
        self.startButton.setGeometry(QtCore.QRect(10, 30, 91, 32))
        self.startButton.setObjectName(_fromUtf8("startButton"))
        self.pauseButton = QtGui.QPushButton(self.controlsBox)
        self.pauseButton.setGeometry(QtCore.QRect(100, 30, 91, 32))
        self.pauseButton.setObjectName(_fromUtf8("pauseButton"))
        self.stopButton = QtGui.QPushButton(self.controlsBox)
        self.stopButton.setGeometry(QtCore.QRect(190, 30, 91, 32))
        self.stopButton.setObjectName(_fromUtf8("stopButton"))
        self.speedBox = QtGui.QSpinBox(self.controlsBox)
        self.speedBox.setGeometry(QtCore.QRect(206, 77, 71, 25))
        self.speedBox.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.speedBox.setMinimum(1)
        self.speedBox.setMaximum(1000)
        self.speedBox.setProperty("value", 100)
        self.speedBox.setObjectName(_fromUtf8("speedBox"))
        self.speedLabel = QtGui.QLabel(self.controlsBox)
        self.speedLabel.setGeometry(QtCore.QRect(150, 80, 51, 20))
        self.speedLabel.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.speedLabel.setObjectName(_fromUtf8("speedLabel"))
        MainWindow.setCentralWidget(self.centralWidget)
        self.menuBar = QtGui.QMenuBar(MainWindow)
        self.menuBar.setGeometry(QtCore.QRect(0, 0, 877, 22))
        self.menuBar.setObjectName(_fromUtf8("menuBar"))
        self.menu_Catalog = QtGui.QMenu(self.menuBar)
        self.menu_Catalog.setObjectName(_fromUtf8("menu_Catalog"))
        self.menuSimulation = QtGui.QMenu(self.menuBar)
        self.menuSimulation.setObjectName(_fromUtf8("menuSimulation"))
        MainWindow.setMenuBar(self.menuBar)
        self.mainToolBar = QtGui.QToolBar(MainWindow)
        self.mainToolBar.setObjectName(_fromUtf8("mainToolBar"))
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.mainToolBar)
        self.statusBar = QtGui.QStatusBar(MainWindow)
        self.statusBar.setObjectName(_fromUtf8("statusBar"))
        MainWindow.setStatusBar(self.statusBar)
        self.action_Import = QtGui.QAction(MainWindow)
        self.action_Import.setObjectName(_fromUtf8("action_Import"))
        self.actionView_Data = QtGui.QAction(MainWindow)
        self.actionView_Data.setObjectName(_fromUtf8("actionView_Data"))
        self.actionStart_Simulation = QtGui.QAction(MainWindow)
        self.actionStart_Simulation.setObjectName(_fromUtf8("actionStart_Simulation"))
        self.actionPause_Simulation = QtGui.QAction(MainWindow)
        self.actionPause_Simulation.setObjectName(_fromUtf8("actionPause_Simulation"))
        self.actionStop_Simulation = QtGui.QAction(MainWindow)
        self.actionStop_Simulation.setObjectName(_fromUtf8("actionStop_Simulation"))
        self.menu_Catalog.addAction(self.action_Import)
        self.menu_Catalog.addSeparator()
        self.menu_Catalog.addAction(self.actionView_Data)
        self.menuSimulation.addAction(self.actionStart_Simulation)
        self.menuSimulation.addAction(self.actionPause_Simulation)
        self.menuSimulation.addAction(self.actionStop_Simulation)
        self.menuBar.addAction(self.menu_Catalog.menuAction())
        self.menuBar.addAction(self.menuSimulation.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "ATLAS i.s.", None))
        self.label.setText(_translate("MainWindow", "Earthquake Catalog", None))
        self.controlsBox.setTitle(_translate("MainWindow", "Forecast Controls", None))
        self.simulationCheckBox.setText(_translate("MainWindow", "Simulation", None))
        self.startButton.setText(_translate("MainWindow", "Start", None))
        self.pauseButton.setText(_translate("MainWindow", "Pause", None))
        self.stopButton.setText(_translate("MainWindow", "Stop", None))
        self.speedBox.setSuffix(_translate("MainWindow", "x", None))
        self.speedLabel.setText(_translate("MainWindow", "Speed", None))
        self.menu_Catalog.setTitle(_translate("MainWindow", "&Catalog", None))
        self.menuSimulation.setTitle(_translate("MainWindow", "Simulation", None))
        self.action_Import.setText(_translate("MainWindow", "&Import...", None))
        self.actionView_Data.setText(_translate("MainWindow", "View Data", None))
        self.actionStart_Simulation.setText(_translate("MainWindow", "Start Simulation", None))
        self.actionPause_Simulation.setText(_translate("MainWindow", "Pause Simulation", None))
        self.actionStop_Simulation.setText(_translate("MainWindow", "Stop Simulation", None))

from plots import SeismicityPlotWidget
