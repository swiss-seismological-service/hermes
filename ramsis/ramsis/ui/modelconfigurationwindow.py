# -*- encoding: utf-8 -*-
"""
Controller class for the model configuration window

Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED

"""

import os

from PyQt4 import QtGui, uic

ui_path = os.path.dirname(__file__)
MODEL_CONFIGURATION_WINDOW_PATH = os.path.join(ui_path, 'views',
                                               'modelconfigurationwindow.ui')
Ui_ModelConfigurationWindow = uic.loadUiType(MODEL_CONFIGURATION_WINDOW_PATH)[0]


class ModelConfigurationWindow(QtGui.QDialog):
    def __init__(self):
        super(ModelConfigurationWindow, self).__init__()

        # Setup the user interface
        self.ui = Ui_ModelConfigurationWindow()
        self.ui.setupUi(self)

        # Hook up buttons
        self.ui.saveButton.clicked.connect(self.action_save)
        self.ui.cancelButton.clicked.connect(self.action_cancel)

    def action_save(self):
        self.close()

    def action_cancel(self):
        self.close()
