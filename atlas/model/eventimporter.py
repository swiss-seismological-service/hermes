# -*- encoding: utf-8 -*-
"""
CSV reader for a list of events

Extension to the python default csv reader for event histories
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import csv
import exceptions
from time import mktime, strptime
from datetime import datetime, timedelta


class EventImporter:
    """
    EventImporter assumes that the file to import contains a *date* column that
    either has relative dates (floats) or absolute dates (date string
    according to strptime()

    """

    def __init__(self, csv_file, delimiter=' ', date_field='date'):
        self.file = csv_file
        self.delimiter = delimiter
        self.date_field = date_field
        self.base_date = datetime(1970, 1, 1)
        self.date_format = None
        self._dates_are_relative = None

    @property
    def expects_base_date(self):
        """
        Checks whether the file contains relative dates and the importer expects
        a base date to parse the file.

        Side effect: rewinds the file when called for the first time

        :param path: path to the csv file
        :type path: string

        """

        if self._dates_are_relative is None:
            reader = csv.DictReader(self.file,
                                    delimiter=self.delimiter,
                                    skipinitialspace=True)
            first_row = reader.next()
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