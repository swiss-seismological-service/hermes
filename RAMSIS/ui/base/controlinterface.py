# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Unified interfaces for Qt controls

This helper module provides a unified interface to some of the most commonly
used methods on Qt controls. Here, a control is defined as a widget that
accepts user input.

Clients can interact with this in one of two ways:
- Instantiate a :class:`ControlInterfaceFactory` object
- Use the default factory through the module level functions
  :func:`control_interface` and :func:`register_interface`.

A factory method (:func:`control_interface`) returns the correct interface
implementation given a concrete Qt control widget. While the interfaces defined
in this module are strictly for Qt control classes, users can register their
own interfaces for custom subclasses or replace the default interface with
another one at runtime using :func:`register_interface`.
"""

from PyQt5.QtWidgets import (QCheckBox, QRadioButton, QSpinBox, QDoubleSpinBox,
                             QDateTimeEdit, QLineEdit, QPlainTextEdit,
                             QComboBox)
from RAMSIS.ui.base.utils import utc_to_local, pyqt_local_to_utc_ua


class ControlInterface:
    """ Default Interface for Qt controls """

    def __init__(self, control):
        """
        ControlInterface initializer

        :param control: Control object the interface will operate on.
        """
        self.control = control

    def get_value(self):
        """
        Returns the user input from the underlying control

        :return: User input value
        """
        self.control.value()

    def set_value(self, value):
        """
        Sets a new value on the underlying control

        :param value: Value to set
        """
        self.control.setValue(value)

    def change_signal(self):
        """
        Returns the change signal of the control.

        Returns the signal that is emitted when the user changes a controls
        value.

        :return: Value change signal
        :rtype: PyQt5.QtCore.pyqtSignal
        """
        return self.control.valueChanged


class QCheckBoxInterface(ControlInterface):
    """ Default interface for QCheckBox """
    def get_value(self):
        return self.control.isChecked()

    def set_value(self, value):
        self.control.setChecked(value)

    def change_signal(self):
        return self.control.stateChanged


class QRadioButtonInterface(ControlInterface):
    """ Default interface for QRadioButton """
    def get_value(self):
        return self.control.isDown()

    def set_value(self, value):
        self.control.setDown(value)

    def change_signal(self):
        return self.control.toggled


class QDateTimeEditInterface(ControlInterface):
    """ Default interface for QDateTimeEdit """
    def get_value(self):
        return pyqt_local_to_utc_ua(self.control.dateTime())

    def set_value(self, value):
        self.control.setDateTime(utc_to_local(value))

    def change_signal(self):
        return self.control.editingFinished


class QDateTimeEditInterfaceLocal(QDateTimeEditInterface):
    """
    Local time interface for QDateTimeEdit

    This is an alternative for :class:`QDateTimeEditInterface` that displays
    local time but receives and outputs UTC.
    """
    def get_value(self):
        return self.control.dateTime().toPyDateTime()

    def set_value(self, value):
        if value:
            self.control.setDateTime(value)
        else:
            self.control.clear()

    def change_signal(self):
        return self.control.editingFinished


class QLineEditInterface(ControlInterface):
    """ Default interface for QLineEdit """
    def get_value(self):
        return self.control.text()

    def set_value(self, value):
        self.control.setText(value)

    def change_signal(self):
        return self.control.textChanged


class QPlainTextEditInterface(ControlInterface):
    """ Default interface for QPlainTextEdit """
    def get_value(self):
        return self.control.toPlainText()

    def set_value(self, value):
        self.control.setPlainText(value)

    def change_signal(self):
        return self.control.textChanged


class QComboBoxInterface(ControlInterface):
    """
    Default interface for QComboBox

    The default interface works on the `data` attribute of each combo box item.
    """
    def get_value(self):
        return self.control.currentData()

    def set_value(self, value):
        self.control.setCurrentIndex(self.control.findData(value))

    def change_signal(self):
        return self.control.currentIndexChanged


class ControlInterfaceFactory:
    """ Factory for known Qt control interfaces """

    def __init__(self):
        self._interfaces = {
            QCheckBox: QCheckBoxInterface,
            QRadioButton: QRadioButtonInterface,
            QSpinBox: ControlInterface,
            QDoubleSpinBox: ControlInterface,
            QDateTimeEdit: QDateTimeEditInterface,
            QLineEdit: QLineEditInterface,
            QPlainTextEdit: QPlainTextEditInterface,
            QComboBox: QComboBoxInterface
        }

    def control_interface(self, control):
        """
        Return the control interface for `control`

        :param control: Qt control widget or custom control
        :returns: Control interface for control
        :rtype: ControlInterface
        """
        return self._interfaces[type(control)](control)

    def register_interface(self, control_class, interface_class):
        """
        Register interface

        Register a new interface for a custom control or replace an existing
        interface.

        :param type control_class: The class (type) of the control
        :param type[ControlInterface] interface_class: The interface class
        """
        self._interfaces[control_class] = interface_class


_default_factory = ControlInterfaceFactory()


def control_interface(control):
    """
    Return the default control interface for `control`

    :param control: Qt control widget or custom control
    :returns: Default control interface for control
    :rtype: ControlInterface
    """
    return _default_factory.control_interface(control)


def register_interface(control_class, interface_class):
    """
    Register default interface

    Register a new default interface for a custom control or replace an
    existing interface.

    :param type control_class: The class (type) of the control
    :param type[ControlInterface] interface_class: The interface class
    """
    _default_factory.register_interface(control_class, interface_class)
