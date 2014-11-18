# -*- encoding: utf-8 -*-
"""
Unit test for the HydraulicEventHistory class
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from datetime import timedelta, datetime

from mock import MagicMock

from data.hydraulicevent import HydraulicEvent
from data.project.hydrauliceventhistory import HydraulicEventHistory
from testeventhistory import MockStore


class BasicOperation(unittest.TestCase):
    """ Tests basic operation """

    def setUp(self):
        """ Create a mock store for the history under test """
        self.mock_store = MockStore()
        self.history = HydraulicEventHistory(self.mock_store)
        base_date = datetime(2013, 3, 15)
        self.expected = []
        for i in range(3):
            date = base_date + timedelta(seconds=i)
            event = HydraulicEvent(date,
                                   flow_dh=(-82.0 - i*0.1),
                                   flow_xt=(132.0 + i*0.1),
                                   pr_dh=(719 + i*0.1),
                                   pr_xt=(269 + i*0.1))
            self.expected.append(event)

        def mock_iter():
            for e in self.expected:
                row = {'flow_dh': e.flow_dh,
                       'flow_xt': e.flow_xt,
                       'pr_dh': e.pr_dh,
                       'pr_xt': e.pr_xt}
                yield e.date_time, row

        self.mock_importer = MagicMock()
        self.mock_importer.__iter__.side_effect = mock_iter

    def test_import(self):
        """ Test if the event import works as expected """
        self.history.import_events(self.mock_importer)
        self.mock_store.purge.assert_called_once_with(HydraulicEvent)
        self.mock_store.add.assert_called_once_with(self.expected)


if __name__ == '__main__':
    unittest.main()
