# -*- encoding: utf-8 -*-
"""
Unit test for the event simulator
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from PyQt4 import QtCore
from datetime import datetime, timedelta
from time import sleep
from model.simulator import Simulator

# Sets the test speed to 10x. If run on a busy system where the delivery of
# timer events is delayed, this might have to be decreased
TEST_SPEED = 10.0

class SignalEmitter(QtCore.QObject):
    """
    The only purpose of this class is to provide the test signal (since this
    is only possible from a class that inherits from QObject)

    """
    test_signal = QtCore.pyqtSignal()


class BasicOperation(unittest.TestCase):
    """ Basic operation of the simulator """

    def setUp(self):
        """
        Test Preparation

        The simulator should deliver the time change signal in intervals of
        one second divided by TEST_SPEED.
        Since the simulator delivers event through the QtCore event loop, we
        need to setup a qt application.

        """
        self.app = QtCore.QCoreApplication([])
        self.history = []
        self.time_step = 1/TEST_SPEED
        self.simulator = Simulator(self.callback)
        self.simulator.speed = TEST_SPEED
        # state variables
        self.simulation_time = None
        self.t_elapsed = 0

    def callback(self, t):
        self.simulation_time = t

    def configure_time_range(self, seconds):
        start = datetime(2013, 12, 4, 9)
        end = start + timedelta(seconds=seconds)
        self.simulator.time_range = (start, end)

    def step_time(self):
        """ a helper function that increases the time step """
        sleep(self.time_step)
        self.t_elapsed += self.time_step

    def test_delivery(self):
        """ Tests signal delivery by the simulator """
        duration = 2
        max_t = (duration + 1.5) / TEST_SPEED
        min_t = (duration - 0.2) / TEST_SPEED
        self.configure_time_range(duration)
        self.simulator.start()

        while (self.t_elapsed < max_t and
               (self.simulation_time is None or
                self.simulation_time < self.simulator.time_range[1])):
            self.app.processEvents()
            self.step_time()
        self.assertLess(self.t_elapsed, max_t,
                        'Events were not delivered in time (' +
                        str(self.t_elapsed) +
                        ')')
        self.assertGreater(self.t_elapsed, min_t,
                           'Event delivery too fast')

    def test_start_with_external_signal(self):
        signal_emmiter = SignalEmitter()
        self.configure_time_range(3600)
        start_time = self.simulator.time_range[0]
        dt = timedelta(seconds=1800)
        self.simulator.start_on_external_signal(signal_emmiter.test_signal, dt)
        self.assertEqual(self.simulation_time, start_time + dt,
                         'First step was not executed immediately')
        signal_emmiter.test_signal.emit()
        self.app.processEvents()
        self.assertEqual(self.simulation_time, start_time + 2 * dt,
                         'Simulator did not step on external signal')
        # The simulation should now be finished
        signal_emmiter.test_signal.emit()
        self.app.processEvents()
        self.assertEqual(self.simulation_time, start_time + 2 * dt,
                         'Simulator has not ended as expected')

    def test_pause(self):
        """ Tests pausing the simulator """
        duration = 3
        max_t = 8 / TEST_SPEED
        min_t = 5 / TEST_SPEED
        self.configure_time_range(duration)
        self.simulator.start()

        # No events should be delivered during the pause
        while (self.t_elapsed < max_t and
               (self.simulation_time is None or
                self.simulation_time < self.simulator.time_range[1])):
            self.app.processEvents()
            if self.t_elapsed == 2/TEST_SPEED:
                self.simulator.pause()
            elif self.t_elapsed == 5/TEST_SPEED:
                self.simulator.start()
            self.step_time()
        self.assertLess(self.t_elapsed, max_t,
                        'Events were not delivered in time (' +
                        str(self.t_elapsed) +
                        ')')
        self.assertGreater(self.t_elapsed, min_t,
                           'Event delivery too fast')

    def test_stop(self):
        """ Tests premature simulation stop """
        duration = 3
        max_t = 5 / TEST_SPEED
        self.configure_time_range(duration)
        self.simulator.start()

        while self.t_elapsed < max_t:
            self.app.processEvents()
            if self.t_elapsed == 2/TEST_SPEED:
                self.simulator.stop()
            self.step_time()
        self.assertLess(self.simulation_time, self.simulator.time_range[1])


if __name__ == '__main__':
    unittest.main()
