# -*- encoding: utf-8 -*-
"""
Provides the Project class which handles project data and state
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from PyQt4 import QtCore
from store import Store


class Project(QtCore.QObject):
    """
    The Project class manages persistent and non-persistent project specific
    data through it's associated data store.

    """

    will_close = QtCore.pyqtSignal(object)

    def __init__(self, store):
        """
        Creates a project by opening the store given in the argument. The
        project will take ownership of the store and will manage all further
        interaction with it.

        :param store: Data store for the project
        :type store: Store

        """
        super(Project, self).__init__()
        self._store = store

    def close(self):
        """
        Closes the project file. Before closing, the *will_close* signal is
        emitted. After closing, the project is not usable anymore and will have
        to be reinstatiated if it is needed again.

        """
        self.will_close.emit(self)
        self._store.close()