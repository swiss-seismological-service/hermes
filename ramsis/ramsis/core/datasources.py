# -*- encoding: utf-8 -*-
"""
Provides tools to receive and import data

All event importers must be implemented as iterators who yield one event
per iteration in the form of (date, row) where date is a datetime object and
row is a dictionary containing at least the fields

    - date
    - x
    - y
    - depth
    - mag

Hydraulic data importers are same but with the fields

    - flow_dh
    - flow_xt
    - pr_dh
    - pr_xt

Data sources receive data from a web service or other data source in the
background. The data is returned by firing a pyqtSignal with the payload

    {'importer': importer, 'time_range': (start_time, end_time)}

The importer will yield the imported events and the time_range contains the
requested time_range as a tuple. The time_range tuple members can be None if no
start or end time was specified.

Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED

"""

import csv
import logging
import exceptions
from time import strptime, mktime
from datetime import datetime, timedelta
from PyQt4 import QtCore
from obspy.clients import fdsn

import core.tools.hydws


class ObsPyCatalogImporter:
    """ Imports event data from an obspy catalog """

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
            origin = event.preferred_origin()
            magnitude = event.preferred_magnitude()
            if not (hasattr(origin, 'depth') and hasattr(magnitude, 'mag')):
                continue

            date = origin.time.datetime
            row = {
                'lat': origin.latitude,
                'lon': origin.longitude,
                'depth': origin.depth,
                'mag': magnitude.mag
            }
            yield (date, row)


class CsvEventImporter:
    """
    Imports seismic events from a csv file

    CsvEventImporter assumes that the file to import contains a *date* column
    that either has relative dates (floats) or absolute dates (date string
    according to strptime()

    """

    def __init__(self, csv_file, delimiter=' ', date_field='date'):
        """
        Creates a new importer to read a csv file. EventImporter expects a
        file that is ready for reading, i.e. it needs to be opened externally

        :param csv_file: file handle
        :param delimiter: single character that delimits the columns
        :param date_field: name of the column that contains the date

        """
        self.file = csv_file
        self.delimiter = delimiter
        self.date_field = date_field
        self.base_date = datetime(1970, 1, 1)
        self.date_format = None
        self._dates_are_relative = None

    @property
    def expects_base_date(self):
        """
        Checks whether the file contains relative dates and the importer
        expects a base date to parse the file.

        Side effect: rewinds the file when called for the first time

        """

        if self._dates_are_relative is None:
            reader = csv.DictReader(self.file,
                                    delimiter=self.delimiter,
                                    skipinitialspace=True)
            first_row = next(reader)
            date = first_row[self.date_field]
            self._dates_are_relative = True
            try:
                float(date)
            except exceptions.ValueError:
                self._dates_are_relative = False
            self.file.seek(0)

        return self._dates_are_relative

    def __iter__(self):
        """
        Iterator for the importer. Parses rows and returns the data in a tuple.

        The tuple contains the absolute date of the event and a dictionary
        with all fields that were read.

        """
        reader = csv.DictReader(self.file,
                                delimiter=self.delimiter,
                                skipinitialspace=True)

        for row in reader:
            if self._dates_are_relative:
                days = float(row[self.date_field])
                date = self.base_date + timedelta(days=days)
            else:
                time_struct = strptime(row[self.date_field], self.date_format)
                date = datetime.fromtimestamp(mktime(time_struct))

            yield (date, row)


class HYDWSCatalogImporter:
    """ Imports hydraulic data from hydws event dicts """

    def __init__(self, catalog):
        self.catalog = catalog

    def __iter__(self):
        for event in self.catalog:
            date = event['time']['value']
            date = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
            row = {
                'flow_dh': event['bottomHoleFlowRate']['value'],
                'flow_xt': event['topHoleFlowRate']['value'],
                'pr_dh': event['bottomHolePressure']['value'],
                'pr_xt': event['topHolePressure']['value']
            }
            yield (date, row)


class HYDWSDataSource(QtCore.QThread):
    """
    Fetches hydraulic data from a web service in the background.

    """

    data_received = QtCore.pyqtSignal(object)

    def __init__(self, url):
        super(HYDWSDataSource, self).__init__()
        self.url = url
        self._logger = logging.getLogger(__name__)
        self._args = {}
        self._logger.info('HYDWS data source: {}'.format(url))
        self.enabled = False

    def fetch(self, **kwargs):
        """
        Fetch data in the background

        If kwargs contains starttime and endtime, these are returned together
        with the results so that the receiver of the event knows which time
        range was requested.

        :param kwargs: args dict forwarded to the fdsnws client

        """
        self._args = kwargs
        if self.enabled:
            self.start()

    def run(self):
        client = core.tools.hydws.Client(self.url)
        args = self._args
        try:
            data_set = client.get_events(**args)
        except core.tools.hydws.HYDWSException as e:
            self._logger.error('HYDWSException: ' + str(e))
            self.data_received.emit(None)
            return

        result = {
            'importer': HYDWSDataSource(data_set),
            'time_range': [args.get(a) for a in ['starttime', 'endtime']]
        }
        self.data_received.emit(result)


class FDSNWSDataSource(QtCore.QThread):
    """
    Fetches seismic event data from a web service in the background.

    """

    data_received = QtCore.pyqtSignal(object)

    def __init__(self, url):
        super(FDSNWSDataSource, self).__init__()
        self.url = url
        self._logger = logging.getLogger(__name__)
        self._args = {}
        self._logger.info('FDSN data source: {}'.format(url))
        self.enabled = False

    def fetch(self, **kwargs):
        """
        Fetch data in the background

        If kwargs contains starttime and endtime, these are returned together
        with the results so that the receiver of the event knows which time
        range was requested.

        :param kwargs: args dict forwarded to the fdsnws client

        """
        self._args = kwargs
        if self.enabled:
            self.start()

    def run(self):
        client = fdsn.Client(self.url)
        args = self._args
        try:
            catalog = client.get_events(**args)
        except fdsn.header.FDSNException as e:
            if 'No data available' in str(e):
                self._logger.info('No data available between {} and {}'
                                  .format(self._args['starttime'],
                                          self._args['endtime']))
            else:
                self._logger.error('FDSNException: ' + str(e))
            self.data_received.emit(None)
        else:
            result = {
                'importer': ObsPyCatalogImporter(catalog),
                'time_range': [args.get(a) for a in ['starttime', 'endtime']]
            }
            self.data_received.emit(result)
