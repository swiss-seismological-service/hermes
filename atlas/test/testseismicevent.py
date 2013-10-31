# -*- encoding: utf-8 -*-
"""
Unit test for the SeismicEvent class

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from datetime import datetime, timedelta
from model.seismicevent import SeismicEvent
from model.location import Location

class BasicOperation(unittest.TestCase):
    """ Test basic operation """

    def test_comparison(self):
        """ Test if two seismic events compare equal """
        date = datetime.now()
        location1 = Location(7.5, 47.5, -100)
        location2 = Location(7.6, 47.5, -100)
        event_a = SeismicEvent(date, 3.4, location1)
        event_b = SeismicEvent(date, 3.4, location1)
        event_c = SeismicEvent(date, 3.4, location2)
        self.assertEqual(event_a, event_b)
        self.assertNotEqual(event_a, event_c)


if __name__ == '__main__':
    unittest.main()
