# -*- encoding: utf-8 -*-
"""
Controller class for the model configuration window

Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED

"""

import json
import os

from PyQt5 import QtGui, uic

ui_path = os.path.dirname(__file__)
MODEL_CONFIGURATION_WINDOW_PATH = os.path.join(ui_path, 'views',
                                               'modelconfigurationwindow.ui')
Ui_ModelConfigurationWindow = uic.loadUiType(MODEL_CONFIGURATION_WINDOW_PATH)[0]


class ModelConfigurationWindow(QtGui.QDialog):
    def __init__(self, project, model):
        super(ModelConfigurationWindow, self).__init__()
        self.project = project
        self.model = model

        # Setup the user interface
        self.ui = Ui_ModelConfigurationWindow()
        self.ui.setupUi(self)

        # Set title
        self.setWindowTitle("{} model configuration".format(self.model))

        # Show current settings
        settings = self.project.settings['forecast_models'][self.model]
        self.ui.titleLineEdit.clear()
        self.ui.titleLineEdit.insert(settings['title'])
        self.ui.urlLineEdit.clear()
        self.ui.urlLineEdit.insert(settings['url'])
        self.ui.paramsTextEdit.clear()
        self.ui.paramsTextEdit.append(json.dumps(settings['parameters']))

        # Hook up buttons
        self.ui.saveButton.clicked.connect(self.action_save)
        self.ui.cancelButton.clicked.connect(self.action_cancel)

    def action_save(self):
        title = self.ui.titleLineEdit.text()
        url = self.ui.urlLineEdit.text()
        params = json.loads(self.ui.paramsTextEdit.toPlainText())
        self.project.settings['forecast_models'][self.model]['title'] = title
        self.project.settings['forecast_models'][self.model]['url'] = url
        self.project.settings['forecast_models'][self.model]['parameters'] = \
            params
        self.project.settings.commit()
        self.project.store.commit()
        self.close()

    def action_cancel(self):
        self.close()
