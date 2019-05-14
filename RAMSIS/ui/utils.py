# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
RAMSIS specific ui utils

"""

import os
from PyQt5 import uic

#: Base path for relative .ui paths in :func:`UiForm`
FORM_BASE_PATH = os.path.join(os.path.dirname(__file__), 'views')


def UiForm(ui_path):
    """
    Mixin to load a ui from a QtCreator .ui file

    The mixin will load the ui elements into the `ui` member of the target
    object.

    :param str ui_path: Path to the ui form. Will be prefixed with the module
        wide `form_base_path`

    """
    form_path = os.path.join(FORM_BASE_PATH, ui_path)
    Ui_Form = uic.loadUiType(form_path)[0]

    class UiFormMixin:
        def __init__(self, *args, **kwargs):
            self.ui = Ui_Form()
            self.ui.setupUi(self)

    return UiFormMixin
