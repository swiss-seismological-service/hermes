from datetime import datetime, timedelta
import logging

from PyQt4 import QtCore

from obspy import UTCDateTime
from obspy.fdsn import Client
from obspy.fdsn.header import FDSNException

import hydws
from hydwscatalogimporter import HYDWSCatalogImporter


class FDSNWSImporter(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)

    def __init__(self, project, settings):
        QtCore.QObject.__init__(self)

        self._project = project
        self._settings = settings
        self.fdsnws_previous_end_time = None
        self._logger = logging.getLogger(__name__)

    def import_fdsnws_data(self):
        if not self._settings.value('data_acquisition/fdsnws_enabled'):
            return
        minutes = self._settings.value('data_acquisition/fdsnws_length')
        url = self._settings.value('data_acquisition/fdsnws_url')
        now = datetime.now()
        if self.fdsnws_previous_end_time:
            starttime = self.fdsnws_previous_end_time
        else:
            starttime = UTCDateTime(now - timedelta(minutes=1440))
        endtime = UTCDateTime(now)
        timerange = (starttime.datetime, endtime.datetime)
        client = Client(url)
        try:
            catalog = client.get_events(starttime=starttime, endtime=endtime)
        except FDSNException as e:
            self._logger.error('FDSNException: ' + str(e))
            self.finished.emit('')
            return
        importer = _ObsPyCatalogImporter(catalog)
        self._project.seismic_history.import_events(importer, timerange)
        self.fdsnws_previous_end_time = endtime

        self.finished.emit('')


class HYDWSImporter(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)

    def __init__(self, project, settings):
        QtCore.QObject.__init__(self)

        self._project = project
        self._settings = settings
        self.hydws_previous_end_time = None
        self._logger = logging.getLogger(__name__)

    def import_hydws_data(self):
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
            self.finished.emit('')
            return
        importer = HYDWSCatalogImporter(catalog)
        self.project.hydraulic_history.import_events(importer, timerange)
        self.hydws_previous_end_time = endtime

        self.finished.emit('')


class _ObsPyCatalogImporter:

    def __init__(self, catalog):
        self.catalog = catalog

    def __iter__(self):
        """
        Iterator for the importer. Parses events and returns the data in a
        tuple.

        The tuple contains the absolute date of the event and a dictionary
        with the location and magnitude of the event.

        """
        for event in self.catalog:
            # TODO: get origin lat/long and convert to cartesian coordinates
            origin = event.preferred_origin()
            magnitude = event.preferred_magnitude()
            if not (hasattr(origin, 'depth') and hasattr(magnitude, 'mag')):
                continue

            date = origin.time.datetime
            row = {
                'x': 1.0,
                'y': 1.0,
                'depth': origin.depth,
                'mag': magnitude.mag
            }
            yield (date, row)
