# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settingswindow.ui'
#
# Created: Wed Jan 15 09:59:47 2014
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

class Ui_SettingsWindow(object):
    def setupUi(self, SettingsWindow):
        SettingsWindow.setObjectName(_fromUtf8("SettingsWindow"))
        SettingsWindow.resize(766, 548)
        self.settingsTabs = QtGui.QTabWidget(SettingsWindow)
        self.settingsTabs.setGeometry(QtCore.QRect(10, 10, 741, 471))
        self.settingsTabs.setTabShape(QtGui.QTabWidget.Rounded)
        self.settingsTabs.setObjectName(_fromUtf8("settingsTabs"))
        self.tabGeneral = QtGui.QWidget()
        self.tabGeneral.setObjectName(_fromUtf8("tabGeneral"))
        self.enableLabModeCheckBox = QtGui.QCheckBox(self.tabGeneral)
        self.enableLabModeCheckBox.setGeometry(QtCore.QRect(20, 50, 211, 18))
        self.enableLabModeCheckBox.setChecked(True)
        self.enableLabModeCheckBox.setObjectName(_fromUtf8("enableLabModeCheckBox"))
        self.openLastProjectOnStartup = QtGui.QCheckBox(self.tabGeneral)
        self.openLastProjectOnStartup.setGeometry(QtCore.QRect(20, 80, 191, 18))
        self.openLastProjectOnStartup.setChecked(True)
        self.openLastProjectOnStartup.setObjectName(_fromUtf8("openLastProjectOnStartup"))
        self.settingsTabs.addTab(self.tabGeneral, _fromUtf8(""))
        self.tabSimulation = QtGui.QWidget()
        self.tabSimulation.setObjectName(_fromUtf8("tabSimulation"))
        self.groupBox = QtGui.QGroupBox(self.tabSimulation)
        self.groupBox.setGeometry(QtCore.QRect(20, 20, 691, 91))
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.speedLabel = QtGui.QLabel(self.groupBox)
        self.speedLabel.setGeometry(QtCore.QRect(214, 63, 51, 20))
        self.speedLabel.setText(_fromUtf8(""))
        self.speedLabel.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.speedLabel.setObjectName(_fromUtf8("speedLabel"))
        self.speedBox = QtGui.QSpinBox(self.groupBox)
        self.speedBox.setEnabled(False)
        self.speedBox.setGeometry(QtCore.QRect(215, 55, 71, 25))
        self.speedBox.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.speedBox.setMinimum(1)
        self.speedBox.setMaximum(10000)
        self.speedBox.setProperty("value", 1000)
        self.speedBox.setObjectName(_fromUtf8("speedBox"))
        self.simulateAFAPRadioButton = QtGui.QRadioButton(self.groupBox)
        self.simulateAFAPRadioButton.setGeometry(QtCore.QRect(20, 30, 161, 18))
        self.simulateAFAPRadioButton.setChecked(True)
        self.simulateAFAPRadioButton.setObjectName(_fromUtf8("simulateAFAPRadioButton"))
        self.simuateAtSpeedFactorRadioButton = QtGui.QRadioButton(self.groupBox)
        self.simuateAtSpeedFactorRadioButton.setGeometry(QtCore.QRect(20, 60, 191, 18))
        self.simuateAtSpeedFactorRadioButton.setObjectName(_fromUtf8("simuateAtSpeedFactorRadioButton"))
        self.settingsTabs.addTab(self.tabSimulation, _fromUtf8(""))
        self.tabForecasting = QtGui.QWidget()
        self.tabForecasting.setObjectName(_fromUtf8("tabForecasting"))
        self.schedulingBox = QtGui.QGroupBox(self.tabForecasting)
        self.schedulingBox.setGeometry(QtCore.QRect(20, 20, 691, 101))
        self.schedulingBox.setObjectName(_fromUtf8("schedulingBox"))
        self.forecastIntervalLabel = QtGui.QLabel(self.schedulingBox)
        self.forecastIntervalLabel.setGeometry(QtCore.QRect(10, 30, 151, 20))
        self.forecastIntervalLabel.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.forecastIntervalLabel.setObjectName(_fromUtf8("forecastIntervalLabel"))
        self.forecastIntervalBox = QtGui.QSpinBox(self.schedulingBox)
        self.forecastIntervalBox.setEnabled(True)
        self.forecastIntervalBox.setGeometry(QtCore.QRect(190, 26, 71, 25))
        self.forecastIntervalBox.setAutoFillBackground(False)
        self.forecastIntervalBox.setFrame(True)
        self.forecastIntervalBox.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.forecastIntervalBox.setMinimum(1)
        self.forecastIntervalBox.setMaximum(24)
        self.forecastIntervalBox.setProperty("value", 6)
        self.forecastIntervalBox.setObjectName(_fromUtf8("forecastIntervalBox"))
        self.rateIntervalBox = QtGui.QSpinBox(self.schedulingBox)
        self.rateIntervalBox.setEnabled(True)
        self.rateIntervalBox.setGeometry(QtCore.QRect(190, 56, 71, 25))
        self.rateIntervalBox.setAutoFillBackground(False)
        self.rateIntervalBox.setFrame(True)
        self.rateIntervalBox.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.rateIntervalBox.setMinimum(1)
        self.rateIntervalBox.setMaximum(60)
        self.rateIntervalBox.setProperty("value", 1)
        self.rateIntervalBox.setObjectName(_fromUtf8("rateIntervalBox"))
        self.rateIntervalLabel = QtGui.QLabel(self.schedulingBox)
        self.rateIntervalLabel.setGeometry(QtCore.QRect(10, 60, 171, 20))
        self.rateIntervalLabel.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.rateIntervalLabel.setObjectName(_fromUtf8("rateIntervalLabel"))
        self.forLabel = QtGui.QLabel(self.schedulingBox)
        self.forLabel.setGeometry(QtCore.QRect(280, 30, 31, 20))
        self.forLabel.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.forLabel.setObjectName(_fromUtf8("forLabel"))
        self.forecastBinNoBox = QtGui.QSpinBox(self.schedulingBox)
        self.forecastBinNoBox.setEnabled(True)
        self.forecastBinNoBox.setGeometry(QtCore.QRect(310, 26, 71, 25))
        self.forecastBinNoBox.setAutoFillBackground(False)
        self.forecastBinNoBox.setFrame(True)
        self.forecastBinNoBox.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.forecastBinNoBox.setMinimum(1)
        self.forecastBinNoBox.setMaximum(6)
        self.forecastBinNoBox.setProperty("value", 6)
        self.forecastBinNoBox.setObjectName(_fromUtf8("forecastBinNoBox"))
        self.forecastBinTimeBox = QtGui.QSpinBox(self.schedulingBox)
        self.forecastBinTimeBox.setEnabled(True)
        self.forecastBinTimeBox.setGeometry(QtCore.QRect(390, 26, 71, 25))
        self.forecastBinTimeBox.setAutoFillBackground(False)
        self.forecastBinTimeBox.setFrame(True)
        self.forecastBinTimeBox.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.forecastBinTimeBox.setMinimum(1)
        self.forecastBinTimeBox.setMaximum(24)
        self.forecastBinTimeBox.setProperty("value", 6)
        self.forecastBinTimeBox.setObjectName(_fromUtf8("forecastBinTimeBox"))
        self.futureLabel = QtGui.QLabel(self.schedulingBox)
        self.futureLabel.setGeometry(QtCore.QRect(470, 30, 91, 20))
        self.futureLabel.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.futureLabel.setObjectName(_fromUtf8("futureLabel"))
        self.outputBox = QtGui.QGroupBox(self.tabForecasting)
        self.outputBox.setGeometry(QtCore.QRect(20, 260, 691, 100))
        self.outputBox.setObjectName(_fromUtf8("outputBox"))
        self.writeResultsToFileCheckBox = QtGui.QCheckBox(self.outputBox)
        self.writeResultsToFileCheckBox.setGeometry(QtCore.QRect(10, 30, 221, 20))
        self.writeResultsToFileCheckBox.setChecked(True)
        self.writeResultsToFileCheckBox.setObjectName(_fromUtf8("writeResultsToFileCheckBox"))
        self.outputPathLabel = QtGui.QLabel(self.outputBox)
        self.outputPathLabel.setGeometry(QtCore.QRect(180, 65, 251, 20))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.outputPathLabel.setFont(font)
        self.outputPathLabel.setObjectName(_fromUtf8("outputPathLabel"))
        self.selectOutputDirButton = QtGui.QPushButton(self.outputBox)
        self.selectOutputDirButton.setGeometry(QtCore.QRect(30, 60, 141, 32))
        self.selectOutputDirButton.setObjectName(_fromUtf8("selectOutputDirButton"))
        self.clearOutputDirButton = QtGui.QPushButton(self.outputBox)
        self.clearOutputDirButton.setGeometry(QtCore.QRect(520, 60, 161, 32))
        self.clearOutputDirButton.setObjectName(_fromUtf8("clearOutputDirButton"))
        self.modelsBox = QtGui.QGroupBox(self.tabForecasting)
        self.modelsBox.setGeometry(QtCore.QRect(20, 130, 691, 121))
        self.modelsBox.setObjectName(_fromUtf8("modelsBox"))
        self.enableRjCheckBox = QtGui.QCheckBox(self.modelsBox)
        self.enableRjCheckBox.setEnabled(False)
        self.enableRjCheckBox.setGeometry(QtCore.QRect(10, 30, 141, 18))
        self.enableRjCheckBox.setChecked(True)
        self.enableRjCheckBox.setObjectName(_fromUtf8("enableRjCheckBox"))
        self.entableEtasCheckBox = QtGui.QCheckBox(self.modelsBox)
        self.entableEtasCheckBox.setEnabled(False)
        self.entableEtasCheckBox.setGeometry(QtCore.QRect(10, 60, 141, 18))
        self.entableEtasCheckBox.setChecked(True)
        self.entableEtasCheckBox.setObjectName(_fromUtf8("entableEtasCheckBox"))
        self.rjConfigButton = QtGui.QPushButton(self.modelsBox)
        self.rjConfigButton.setEnabled(False)
        self.rjConfigButton.setGeometry(QtCore.QRect(180, 25, 110, 32))
        self.rjConfigButton.setObjectName(_fromUtf8("rjConfigButton"))
        self.etasConfigButton = QtGui.QPushButton(self.modelsBox)
        self.etasConfigButton.setEnabled(False)
        self.etasConfigButton.setGeometry(QtCore.QRect(180, 55, 110, 32))
        self.etasConfigButton.setObjectName(_fromUtf8("etasConfigButton"))
        self.settingsTabs.addTab(self.tabForecasting, _fromUtf8(""))
        self.okButton = QtGui.QPushButton(SettingsWindow)
        self.okButton.setGeometry(QtCore.QRect(640, 500, 110, 32))
        self.okButton.setObjectName(_fromUtf8("okButton"))
        self.resetToDefaultButton = QtGui.QPushButton(SettingsWindow)
        self.resetToDefaultButton.setGeometry(QtCore.QRect(10, 500, 131, 32))
        self.resetToDefaultButton.setObjectName(_fromUtf8("resetToDefaultButton"))

        self.retranslateUi(SettingsWindow)
        self.settingsTabs.setCurrentIndex(2)
        QtCore.QMetaObject.connectSlotsByName(SettingsWindow)

    def retranslateUi(self, SettingsWindow):
        SettingsWindow.setWindowTitle(_translate("SettingsWindow", "ATLS Configuration", None))
        self.enableLabModeCheckBox.setToolTip(_translate("SettingsWindow", "In Simulation Mode seismic and hydraulic events are played back from an existing catalog.", None))
        self.enableLabModeCheckBox.setText(_translate("SettingsWindow", "Run AAtlsin Lab Mode", None))
        self.openLastProjectOnStartup.setText(_translate("SettingsWindow", "Open last project on startup", None))
        self.settingsTabs.setTabText(self.settingsTabs.indexOf(self.tabGeneral), _translate("SettingsWindow", "General", None))
        self.groupBox.setTitle(_translate("SettingsWindow", "Simulation Speed", None))
        self.speedBox.setSuffix(_translate("SettingsWindow", "x", None))
        self.simulateAFAPRadioButton.setText(_translate("SettingsWindow", "As fast as possible", None))
        self.simuateAtSpeedFactorRadioButton.setText(_translate("SettingsWindow", "With a specific speed factor:", None))
        self.settingsTabs.setTabText(self.settingsTabs.indexOf(self.tabSimulation), _translate("SettingsWindow", "Lab Mode", None))
        self.schedulingBox.setTitle(_translate("SettingsWindow", "Scheduling", None))
        self.forecastIntervalLabel.setText(_translate("SettingsWindow", "Compute forecasts every", None))
        self.forecastIntervalBox.setSuffix(_translate("SettingsWindow", " h", None))
        self.rateIntervalBox.setSuffix(_translate("SettingsWindow", " min", None))
        self.rateIntervalLabel.setText(_translate("SettingsWindow", "Compute seismic rates every", None))
        self.forLabel.setText(_translate("SettingsWindow", "for", None))
        self.forecastBinNoBox.setSuffix(_translate("SettingsWindow", "x", None))
        self.forecastBinTimeBox.setSuffix(_translate("SettingsWindow", " h", None))
        self.futureLabel.setText(_translate("SettingsWindow", "into the future", None))
        self.outputBox.setTitle(_translate("SettingsWindow", "Output", None))
        self.writeResultsToFileCheckBox.setText(_translate("SettingsWindow", "Write forecasting results to disk", None))
        self.outputPathLabel.setText(_translate("SettingsWindow", "~/Desktop/AtlasResults", None))
        self.selectOutputDirButton.setText(_translate("SettingsWindow", "Output Directory...", None))
        self.clearOutputDirButton.setText(_translate("SettingsWindow", "Clear Output Directory", None))
        self.modelsBox.setTitle(_translate("SettingsWindow", "Models", None))
        self.enableRjCheckBox.setText(_translate("SettingsWindow", "Reasenberg - Jones", None))
        self.entableEtasCheckBox.setText(_translate("SettingsWindow", "ETAS", None))
        self.rjConfigButton.setText(_translate("SettingsWindow", "Configure...", None))
        self.etasConfigButton.setText(_translate("SettingsWindow", "Configure...", None))
        self.settingsTabs.setTabText(self.settingsTabs.indexOf(self.tabForecasting), _translate("SettingsWindow", "Forecasting", None))
        self.okButton.setText(_translate("SettingsWindow", "Ok", None))
        self.resetToDefaultButton.setText(_translate("SettingsWindow", "Reset to Default", None))
