# -*- encoding: utf-8 -*-
# Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED
"""
Provides runners that utilize Qt threading to run tasks in a separate thread

"""

from PyQt4 import QtCore

from importers import FDSNWSImporter, HYDWSImporter


class FDSNWSRunner(QtCore.QObject):
    """
    Start and run a new thread to fetch seismic data from a web service
    and return the results.

    """

    finished = QtCore.pyqtSignal(object)

    def __init__(self, settings):
        QtCore.QObject.__init__(self)

        self._qthread = QtCore.QThread()
        self._importer = FDSNWSImporter(settings)

        self._importer.moveToThread(self._qthread)

        self._qthread.started.connect(self._importer.import_fdsnws_data)
        self._importer.finished.connect(self.on_finished)

    def __del__(self):
        # Make sure the thread ends before we destroy it
        self._qthread.quit()
        self._qthread.wait()

    def start(self, project_time):
        self._importer.project_time = project_time
        self._qthread.start()

    def on_finished(self, results):
        """
        Finished handler. Returns results from the web service and quits the
        thread.

        """

        self.finished.emit(results)

        self._qthread.quit()
        self._qthread.wait()


class HYDWSRunner(QtCore.QObject):
    """
    Start and run a new thread to fetch hydraulic data from a web service
    and return the results.

    """

    finished = QtCore.pyqtSignal(object)

    def __init__(self, settings):
        QtCore.QObject.__init__(self)

        self._qthread = QtCore.QThread()
        self._importer = HYDWSImporter(settings)

        self._importer.moveToThread(self._qthread)

        self._qthread.started.connect(self._importer.import_hydws_data)
        self._importer.finished.connect(self.on_finished)

    def __del__(self):
        # Make sure the thread ends before we destroy it
        self._qthread.quit()
        self._qthread.wait()

    def start(self, project_time):
        self._importer.project_time = project_time
        self._qthread.start()

    def on_finished(self, results):
        """
        Finished handler. Returns results from the web service and quits the
        thread.

        """

        self.finished.emit(results)

        self._qthread.quit()
        self._qthread.wait()
