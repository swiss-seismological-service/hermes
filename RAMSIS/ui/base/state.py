# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
State machine to handle the state of UI controls and labels

"""
import collections
from transitions.extensions import HierarchicalMachine as Machine
from transitions.extensions.states import add_state_features, State


class Enable(State):
    """
    State extension to enable and disable UI controls

    This state extension adds the arguments `ui_enable` and `ui_disable` to the
    `State` initializer. The argument specifies the widgets that shall be
    disabled or enabled upon entering the state or exiting the state. It can
    either be a single widget, a list of widgets or a dict explicitly. By using
    the latter, you can also specify widgets to enable/disable on exiting the
    state.

    Example:

    .. code-block: python

        machine.add_state({'name': 'foo_state', 'ui_disable': [btn1, btn2]}
        machine.add_state({'name': 'bar_state',
                           'ui_enable': {'on_enter': btn3,
                                         'on_exit': [btn3, btn1]}

    .. note: This currently only works on control widgets that implement
             `setEnabled()`.

    """
    def __init__(self, *args, **kwargs):
        self.enable = kwargs.pop('ui_enable', None)
        self.disable = kwargs.pop('ui_disable', None)
        super().__init__(*args, **kwargs)

    def enter(self, event_data):
        enable = self._target_widget_set(enable=True, enter=True)
        disable = self._target_widget_set(enable=False, enter=True)
        for w in enable | disable:
            w.setEnabled(w in enable)
        super().enter(event_data)

    def exit(self, event_data):
        enable = self._target_widget_set(enable=True, enter=False)
        disable = self._target_widget_set(enable=False, enter=False)
        for w in enable | disable:
            w.setEnabled(w in enable)
        super().exit(event_data)

    def _target_widget_set(self, enable, enter):
        member = self.enable if enable else self.disable
        if not member:
            return set()
        elif isinstance(member, dict):
            target = member['on_enter'] if enter else member['on_exit']
        else:
            target = member
        return {*target} if isinstance(target, collections.Iterable) \
            else {target}


class Text(State):
    """
    State extension to set the text on UI labels, buttons, etc

    This state extension adds the argument `ui_text` to the `State`
    initializer. The argument specifies the caption text for each control in a
    dict. Alternatively the widget caption specification can be embedded in a
    wrapper dict that contains separate specifications for `on_enter` and
    `on_exit` events.

    Example:

    .. code-block: python

        machine.add_state({'name': 'foo_state', 'ui_text': {btn1: 'Foo'}}
        machine.add_state({'name': 'bar_state',
                           'ui_text': {'on_enter': {btn1: 'Save'},
                                       'on_exit': {btn1: 'Cancel',
                                                   label1: 'Bar'}}}

    .. note: This currently only supports widgets that implement `setText()`.

    """

    def __init__(self, *args, **kwargs):
        self.text = kwargs.pop('ui_text', {})
        super().__init__(*args, **kwargs)

    def enter(self, event_data):
        for widget, text in self._target_widget_dict(enter=True).items():
            widget.setText(text)
        super().enter(event_data)

    def exit(self, event_data):
        for widget, text in self._target_widget_dict(enter=False).items():
            widget.setText(text)
        super().enter(event_data)

    def _target_widget_dict(self, enter=True):
        if 'on_enter' in self.text or 'on_exit' in self.text:
            return self.text.get('on_enter' if enter else 'on_exit', {})
        else:
            return self.text


@add_state_features(Enable, Text)
class UiStateMachine(Machine):
    pass
