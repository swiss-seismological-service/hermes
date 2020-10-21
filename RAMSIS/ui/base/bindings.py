# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Bindings for Qt Widgets

Bindings provide a way to update model values automatically whenever the
respective Qt widgets displaying the value changes.

.. note: Note that unlike traditional bindings, these are uni-directional
because regular python objects don't emit notifications when attributes change.
The :class:`Binding` does provide a :meth:`~Binding.refresh_ui` method to
update the GUI on request.

"""
import abc

from RAMSIS.utils import rgetattr, rsetattr
from RAMSIS.ui.base.controlinterface import control_interface


class Binding(abc.ABC):
    """  The base class for specific bindings """

    def __init__(self, target, widget):
        """

        :param target: Target model object
        :param QWidget widget: Widget showing the value of the target
        """
        self.target = target
        self.widget = widget
        signal = control_interface(widget).change_signal()
        signal.connect(self.on_widget_changed)

    @property
    def widget_value(self):
        return control_interface(self.widget).get_value()

    @property
    @abc.abstractmethod
    def target_value(self):
        pass

    def refresh_ui(self):
        """ Refresh the UI with the current value from the target """
        if self.target_value:
            control_interface(self.widget).set_value(self.target_value)

    @abc.abstractmethod
    def on_widget_changed(self):
        pass


class AttrBinding(Binding):
    """ Binds a widget to an object attribute """

    def __init__(self, target, attr, widget):
        """

        :param str attr: Attribute to bind to
        """
        super().__init__(target, widget)
        self.attr = attr

    @property
    def target_value(self):
        return rgetattr(self.target, self.attr)

    def on_widget_changed(self):
        rsetattr(self.target, self.attr, self.widget_value)


class DictBinding(Binding):
    """ Binds a widget to a dict entry """

    def __init__(self, target, key, widget):
        """

        :param str key: Dict key used to set or get value on `target`
        """
        super().__init__(target, widget)
        self.key = key

    @property
    def target_value(self):
        return self.target[self.key]

    def on_widget_changed(self):
        self.target[self.key] = self.widget_value


class CallableBinding(Binding):
    """ Binds a widget to a value using a setter and a getter """

    def __init__(self, target, getter, setter, widget):
        """

        :param getter: Getter (must accept a target)
        :param setter: Setter (must accept a target and a value
        """
        super().__init__(target, widget)
        self.getter = getter
        self.setter = setter

    @property
    def target_value(self):
        return self.getter(self.target)

    def on_widget_changed(self):
        self.setter(self.target, self.widget_value)
