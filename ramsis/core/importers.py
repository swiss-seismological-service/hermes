from datetime import datetime, timedelta
import logging

from PyQt4 import QtCore

from obspy import UTCDateTime
from obspy.fdsn import Client
from obspy.fdsn.header import FDSNException

import hydws
from hydwscatalogimporter import HYDWSCatalogImporter
from obspycatalogimporter import ObsPyCatalogImporter


class FDSNWSImporter(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)

    def __init__(self, settings):
        QtCore.QObject.__init__(self)

        self._settings = settings
        self.fdsnws_previous_end_time = None
        self._logger = logging.getLogger(__name__)

    def import_fdsnws_data(self):
        results = self._run()
        self.finished.emit(results)

    def _run(self):
        if not self._settings.value('data_acquisition/fdsnws_enabled'):
            return
        minutes = self._settings.value('data_acquisition/fdsnws_length')
        url = self._settings.value('data_acquisition/fdsnws_url')
        now = datetime.now()
        if self.fdsnws_previous_end_time:
            starttime = self.fdsnws_previous_end_time
        else:
            starttime = UTCDateTime(now - timedelta(minutes=minutes))
        endtime = UTCDateTime(now)
        timerange = (starttime.datetime, endtime.datetime)
        client = Client(url)
        try:
            catalog = client.get_events(starttime=starttime, endtime=endtime)
        except FDSNException as e:
            self._logger.error('FDSNException: ' + str(e))
            self.finished.emit(None)
            return
        importer = ObsPyCatalogImporter(catalog)
        self.fdsnws_previous_end_time = endtime

        results = {
            'importer': importer,
            'timerange': timerange
        }

        return results


class HYDWSImporter(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)

    def __init__(self, settings):
        QtCore.QObject.__init__(self)

        self._settings = settings
        self.hydws_previous_end_time = None
        self._logger = logging.getLogger(__name__)

    def import_hydws_data(self):
        results = self._run()
        self.finished.emit(results)

    def _run(self):
        if not self._settings.value('data_acquisition/hydws_enabled'):
            return
        minutes = self._settings.value('data_acquisition/hydws_length')
        url = self._settings.value('data_acquisition/hydws_url')
        now = datetime.now()
        if self.hydws_previous_end_time:
            starttime = self.hydws_previous_end_time
        else:
            starttime = UTCDateTime(now - timedelta(minutes=minutes))
        endtime = UTCDateTime(now)
        timerange = (starttime.datetime, endtime.datetime)
        client = hydws.Client(url)
        try:
            catalog = client.get_events(starttime=starttime, endtime=endtime)
        except hydws.HYDWSException as e:
            self._logger.error('HYDWSException: ' + str(e))
            self.finished.emit(None)
            return
        importer = HYDWSCatalogImporter(catalog)
        self.hydws_previous_end_time = endtime

        results = {
            'importer': importer,
            'timerange': timerange
        }

        return results
