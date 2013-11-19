# -*- encoding: utf-8 -*-
"""
Unit test for the event simulator
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from collections import namedtuple
from PyQt4 import QtCore
from mock import MagicMock, call
from datetime import datetime
from time import sleep
from model.seismicevent import SeismicEvent
from model.location import Location
from model.simulator import Simulator

# Sets the test speed to 10x. If run on a busy system where the delivery of
# timer events is delayed, this might have to be decreased
TEST_SPEED = 10.0

class BasicOperation(unittest.TestCase):
    """ Basic operation of the simulator """

    def setUp(self):
        """
        Test Preparation

        We setup three events with a temporal distance of 1 second each.
        The simulator should deliver those events in intervals of
        one second divided by TEST_SPEED.
        Since the simulator delivers event through the QtCore event loop, we
        need to setup a qt application.

        """
        self.app = QtCore.QCoreApplication([])
        self.history = []
        location = Location(7.5, 47.5, -100)
        for i in range(3):
            date = datetime(2010, 10, 13, 14, 00, i)
            self.history.append(SeismicEvent(date, 3.2, location))
        self.time_step = 1/TEST_SPEED
        self.simulator = Simulator(self.history, self._callback)
        self.simulator.speed = TEST_SPEED
        # state variables
        self.t_elapsed = 0
        self.num_events = 0

    def tearDown(self):
        self.app.exit()

    def _callback(self, t, num_events, ended):
        self.num_events += num_events

    def step_time(self):
        """ a helper function that increases the time step """
        sleep(self.time_step)
        self.t_elapsed += self.time_step

    def test_delivery(self):
        """ Tests event delivery by the simulator """
        self.simulator.start()
        # All three events from the history should be delivered in
        # approximately 3 time units. We give it a bit of leeway by setting
        # the timeout/assertion a bit higher
        timeout = 5/TEST_SPEED

        while self.t_elapsed < timeout and self.num_events < 3:
            self.app.processEvents()
            self.step_time()
        self.assertLess(self.t_elapsed, 5.5/TEST_SPEED,
                        'Events were not delivered in time (' +
                        str(self.t_elapsed) +
                        ')')
        self.assertGreater(self.t_elapsed, 2.5/TEST_SPEED,
                           'Event delivery too fast')

    def test_pause(self):
        """ Tests pausing the simulator """
        self.simulator.start()

        # All three events from the history should be delivered
        # No events should be delivered during the pause
        while self.t_elapsed < 10/TEST_SPEED and self.num_events < 3:
            self.app.processEvents()
            if self.t_elapsed == 2/TEST_SPEED:
                self.simulator.pause()
            elif self.t_elapsed == 5/TEST_SPEED:
                self.simulator.start()
            self.step_time()
        self.assertLess(self.t_elapsed, 10/TEST_SPEED,
                        'Events were not delivered in time')
        self.assertGreater(self.t_elapsed, 5/TEST_SPEED,
                           'Event delivery too fast')

    def test_stop(self):
        """ Tests premature simulation stop """
        self.simulator.start()

        # Only two events from the history should be delivered
        while self.t_elapsed < 5/TEST_SPEED and self.num_events < 3:
            self.app.processEvents()
            if self.t_elapsed == 2/TEST_SPEED:
                self.simulator.stop()
            self.step_time()
        self.assertEqual(self.num_events, 2)


if __name__ == '__main__':
    unittest.main()
