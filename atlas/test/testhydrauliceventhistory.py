# -*- encoding: utf-8 -*-
"""
Unit test for the HydraulicEventHistory class
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from model.hydraulicevent import HydraulicEvent
from model.hydrauliceventhistory import HydraulicEventHistory
from testeventhistory import MockStore
from datetime import timedelta, datetime


class BasicOperation(unittest.TestCase):
    """ Tests basic operation """

    def setUp(self):
        """ Create a mock store for the history under test """
        self.mock_store = MockStore()
        self.history = HydraulicEventHistory(self.mock_store)

    def test_csv_import(self):
        """ Test if the csv import works as expected """
        base_date = datetime(2013, 3, 15)
        expected = []
        for i in range(3):
            date = base_date + timedelta(seconds=i)
            event = HydraulicEvent(date,
                                   flow_dh=(-82.0 - i*0.1),
                                   flow_xt=(132.0 + i*0.1),
                                   pr_dh=(719 + i*0.1),
                                   pr_xt=(269 + i*0.1))
            expected.append(event)

        date_format = '%Y-%m-%dT%H:%M:%S'
        self.history.import_from_csv('resources/test_hydr.csv', date_format)
        self.mock_store.purge.assert_called_once_with(HydraulicEvent)
        self.mock_store.add.assert_called_once_with(expected)


if __name__ == '__main__':
    unittest.main()
