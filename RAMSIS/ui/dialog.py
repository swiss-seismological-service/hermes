# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Dialog related GUI facilities.
"""

import collections
import json
import logging

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QDialog, QWidget, QFileDialog, QMessageBox
from RAMSIS.io.hydraulics import (
    HYDWSBoreholeHydraulicsDeserializer, HYDWSJSONIOError)
from RAMSIS.io.utils import pymap3d_transform_geodetic2ned
from RAMSIS.ui.utils import UiForm


class ImportInjectionStrategyFromFileDialog(
        QDialog, UiForm('importinjectionstrategyfromfile.ui')):
    """
    UI dialog to import an injection plan from a file.
    """
    LOGGER = 'ramsis.ui.importinjectionstrategyfromfiledialog'

    def __init__(self, *args, **kwargs):
        """
        Dialog initializer
        """
        super().__init__(*args, **kwargs)
        self._data = None

        self.logger = logging.getLogger(self.LOGGER)

    @property
    def data(self):
        return self._data

    @pyqtSlot(name='on_openPushButton_clicked')
    def open_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        path, _ = QFileDialog.getOpenFileName(
            QWidget(), "QFileDialog.getOpenFileName()",
            "", "All Files (*);;Borehole/Hydraulics Scenario (*.json)",
            options=options)

        self.ui.filePathLineEdit.setText(path)

    def _on_accept(self):
        srs = self.ui.sourceSRSLineEdit.text()
        deserializer_args = {'plan': True}
        if srs or srs != 'None':
            # TODO(damb): validate SRS
            deserializer_args.update({
                'proj': srs,
                'transform_callback': pymap3d_transform_geodetic2ned})

        deserializer = HYDWSBoreholeHydraulicsDeserializer(
            **deserializer_args)

        fpath = self.ui.filePathLineEdit.text()
        self.logger.debug(
            f'Importing injection plan {fpath!r}')

        try:
            with open(fpath, 'rb') as ifd:
                self._data = deserializer.load(ifd)
        except (OSError, json.JSONDecodeError, HYDWSJSONIOError) as err:
            _ = QMessageBox.critical(
                self, 'RAMSIS',
                (f'Error while importing data from {fpath!r}:'
                 f'\n{err}.'),
                buttons=QMessageBox.Close)
            self.logger.error(
                f'Importing data from {fpath!r} failed ({err}).')
        else:
            self.logger.info(
                'Injection scenario sucessfully imported.')

    def accept(self):
        self._on_accept()
        super().accept()
