# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
RAMSIS specific ui utils

"""

import os

from PyQt5 import uic

from RAMSIS import wkt_utils
from RAMSIS.ui.base.bindings import AttrBinding

#: Base path for relative .ui paths in :func:`UiForm`
FORM_BASE_PATH = os.path.join(os.path.dirname(__file__), 'views')


def UiForm(ui_path, form_base_path=FORM_BASE_PATH):
    """
    Mixin to load a ui from a QtCreator .ui file

    The mixin will load the ui elements into the `ui` member of the target
    object.

    :param str ui_path: Path to the ui form. Will be prefixed with
        :code:`form_base_path`
    :param str form_base_path: Base path to UI forms

    """
    form_path = os.path.join(form_base_path, ui_path)
    Ui_Form = uic.loadUiType(
        form_path,
        import_from='RAMSIS.ui.views', from_imports=True)[0]

    class UiFormMixin:
        def __init__(self, *args, **kwargs):
            self.ui = Ui_Form()
            self.ui.setupUi(self)

    return UiFormMixin


class WktPointBinding(AttrBinding):
    """
    Binds a widget to a specific dimension of a WKT/WKB point

    .. note: If the Binding is requested to set the coordinate of an otherwise
             uninitialized point, any remaining coordinates will be initialized
             to 0.

    """

    def __init__(self, target, attr, dimension, widget):
        super().__init__(target, attr, widget)
        self.dimension = dimension

    @property
    def target_value(self):
        data = super().target_value
        coords = wkt_utils.coordinates_from_wkb(data)
        return str(coords[self.dimension]) if coords else None

    def on_widget_changed(self):
        data = super().target_value
        coords = list(wkt_utils.coordinates_from_wkb(data)) or [0, 0, 0]
        coords[self.dimension] = float(self.widget_value)
        setattr(self.target, self.attr, wkt_utils.coordinates_to_wkb(coords))
