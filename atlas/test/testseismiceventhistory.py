# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from model.seismicevent import SeismicEvent
from model.seismiceventhistory import SeismicEventHistory
from testeventhistory import MockStore
from datetime import timedelta, datetime
from model.location import Location


class BasicOperation(unittest.TestCase):
    """ Tests basic operation """

    def setUp(self):
        """ Create a mock store for the history under test """
        self.mock_store = MockStore()
        self.history = SeismicEventHistory(self.mock_store)

    def test_csv_import(self):
        """ Test if the csv import works as expected """
        base_date = datetime(2013, 3, 15)
        e1 = SeismicEvent(base_date + timedelta(days=0.17), 0.4,
                          Location(7.5, 47.5, 0))
        e2 = SeismicEvent(base_date + timedelta(days=0.23), 0.8,
                          Location(7.6, 47.6, 0))
        e3 = SeismicEvent(base_date + timedelta(days=0.26), 0.45,
                          Location(7.7, 47.7, 0))
        expected = [e1, e2, e3]

        self.history.import_from_csv('resources/test_catalog.csv',
                                     base_date=base_date)
        self.mock_store.purge.assert_called_once_with(SeismicEvent)
        self.mock_store.add.assert_called_once_with(expected)


if __name__ == '__main__':
    unittest.main()
