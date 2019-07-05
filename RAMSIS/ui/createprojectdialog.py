# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
UI dialog to create a new project

"""

from PyQt5.QtWidgets import QDialog
from RAMSIS.ui.utils import UiForm


class CreateProjectDialog(QDialog, UiForm('createprojectdialog.ui')):
    """
    UI dialog to create a new project

    """
    def __init__(self, callback, *args, **kwargs):
        """
        Dialog initializer

        :param callable callback: Callback to invoke on accept. The callback
            must accept a single argument which is the dialog that was
            accepted.

        """
        super().__init__(*args, **kwargs)
        self.callback = callback

    def accept(self):
        if self.callback:
            self.callback(self)
        super().accept()
