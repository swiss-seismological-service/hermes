"""
PyQt specific utilities (with replacements or mocks where PyQt is not
available.

Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED

"""

try:
    from PyQt4.QtCore import QObject, pyqtSignal
except ImportError:

    class Signal:
        """
        Fake signal implementation

        Connected slots are executed synchronously
        """
        def __init__(self):
            self._connections = set()

        def emit(self, obj):
            for connection in self._connections:
                connection(obj)

        def connect(self, slot):
            self._connections.add(slot)

        def disconnect(self, slot):
            try:
                self._connections.remove(slot)
            except KeyError:
                pass

else:

    class Proxy(QObject):
        sig = pyqtSignal(object)

    class Signal:
        """
        Uses a proxy to emit a pyqtSignal if PyQt is available

        Note that slots connected to Signal must always take one argument

        """
        def __init__(self):
            self._proxy = Proxy()

        def emit(self, obj=None):
            self._proxy.sig.emit(obj)

        def connect(self, slot):
            self._proxy.sig.connect(slot)

        def disconnect(self, slot):
            self._proxy.sig.disconnect(slot)



