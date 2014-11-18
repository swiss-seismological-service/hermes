# -*- encoding: utf-8 -*-
"""
Unit test for the AtlsProject class
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from collections import namedtuple
from datetime import datetime

from mock import patch, MagicMock
from PyQt4 import QtCore

from data.project.atlsproject import AtlsProject


Event = namedtuple('Event', 'date_time')


class AtlsProjectTest(unittest.TestCase):

    def setUp(self):
        """
        Setup fake seismic and hydraulic histories which the project will
        use upon instantiation.

        """
        self.hydraulic_events = [Event(date_time=datetime(2013, 12, 5, 9)),
                                 Event(date_time=datetime(2013, 12, 5, 10))]

        self.seismic_events = [Event(date_time=datetime(2013, 12, 5, 8)),
                               Event(date_time=datetime(2013, 12, 5, 11))]

        def h_get_item(item):
            return self.hydraulic_events[item]

        def s_get_item(item):
            return self.seismic_events[item]

        s_config = {'return_value.__getitem__.side_effect': s_get_item}
        h_config = {'return_value.__getitem__.side_effect': h_get_item}

        self.s_patch = patch('project.atlsproject.SeismicEventHistory',
                             **s_config)
        self.h_patch = patch('project.atlsproject.HydraulicEventHistory',
                             **h_config)
        self.s_mock = self.s_patch.start()
        self.h_mock = self.h_patch.start()

        # Prepare a fake Store object
        self.store_mock = MagicMock()

    def tearDown(self):
        self.s_patch.stop()
        self.h_patch.stop()

    def test_init(self):
        """ Test if the AtlsProject initializes as expected. """
        self.project = AtlsProject(self.store_mock)
        t_expected = self.seismic_events[0].date_time
        self.assertEqual(self.project.project_time, t_expected)

    def test_earliest_no_hydr(self):
        """ Test if the AtlsProject initializes as expected. """
        self.h_mock.return_value.__getitem__.side_effect = None
        self.h_mock.return_value.__getitem__.return_value = None
        self.project = AtlsProject(self.store_mock)
        t_expected = self.seismic_events[0].date_time
        self.assertEqual(self.project.earliest_event().date_time, t_expected)

    def test_earliest_no_seis(self):
        """ Test if the AtlsProject initializes as expected. """
        self.s_mock.return_value.__getitem__.side_effect = None
        self.s_mock.return_value.__getitem__.return_value = None
        self.project = AtlsProject(self.store_mock)
        t_expected = self.hydraulic_events[0].date_time
        self.assertEqual(self.project.earliest_event().date_time, t_expected)

    def test_earliest_no_events(self):
        self.h_mock.return_value.__getitem__.side_effect = None
        self.h_mock.return_value.__getitem__.return_value = None
        self.s_mock.return_value.__getitem__.side_effect = None
        self.s_mock.return_value.__getitem__.return_value = None
        self.project = AtlsProject(self.store_mock)
        self.assertIsNone(self.project.earliest_event())

    def test_event_time_range(self):
        self.project = AtlsProject(self.store_mock)
        expected = (self.seismic_events[0].date_time,
                    self.seismic_events[1].date_time)
        self.assertEqual(self.project.event_time_range(), expected)

    def test_update_project_time(self):
        """ Test if the project_time_changed signal is emitted as expected """
        self.project = AtlsProject(self.store_mock)
        app = QtCore.QCoreApplication([])
        handler = MagicMock()
        self.project.project_time_changed.connect(handler)
        t = datetime(2020, 1, 1, 17)

        self.project.update_project_time(t)
        app.processEvents()
        handler.assert_called_once_with(t)


if __name__ == '__main__':
    unittest.main()
