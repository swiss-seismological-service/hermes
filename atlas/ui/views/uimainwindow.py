# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'views/mainwindow.ui'
#
# Created: Mon Aug 12 09:05:25 2013
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
        MainWindow.resize(400, 300)
        self.centralWidget = QtGui.QWidget(MainWindow)
        self.centralWidget.setObjectName(_fromUtf8("centralWidget"))
        self.label = QtGui.QLabel(self.centralWidget)
        self.label.setGeometry(QtCore.QRect(20, 30, 81, 16))
        self.label.setObjectName(_fromUtf8("label"))
        MainWindow.setCentralWidget(self.centralWidget)
        self.menuBar = QtGui.QMenuBar(MainWindow)
        self.menuBar.setGeometry(QtCore.QRect(0, 0, 400, 22))
        self.menuBar.setObjectName(_fromUtf8("menuBar"))
        self.menu_Catalog = QtGui.QMenu(self.menuBar)
        self.menu_Catalog.setObjectName(_fromUtf8("menu_Catalog"))
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
        self.menu_Catalog.addAction(self.action_Import)
        self.menu_Catalog.addSeparator()
        self.menu_Catalog.addAction(self.actionView_Data)
        self.menuBar.addAction(self.menu_Catalog.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "ATLAS i.s.", None))
        self.label.setText(_translate("MainWindow", "Hello, world!", None))
        self.menu_Catalog.setTitle(_translate("MainWindow", "&Catalog", None))
        self.action_Import.setText(_translate("MainWindow", "&Import...", None))
        self.actionView_Data.setText(_translate("MainWindow", "View Data", None))

