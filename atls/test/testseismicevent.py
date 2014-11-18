# -*- encoding: utf-8 -*-
"""
Unit test for the SeismicEvent class

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from datetime import datetime

from data.seismicevent import SeismicEvent
from data.geometry import Point


class BasicOperation(unittest.TestCase):
    """ Test basic operation """

    def test_comparison(self):
        """ Test if two seismic events compare equal """
        date = datetime.now()
        location1 = Point(10, 100, 1000)
        location2 = Point(11, 200, 1002)
        event_a = SeismicEvent(date, 3.4, location1)
        event_b = SeismicEvent(date, 3.4, location1)
        event_c = SeismicEvent(date, 3.4, location2)
        self.assertEqual(event_a, event_b)
        self.assertNotEqual(event_a, event_c)


if __name__ == '__main__':
    unittest.main()
