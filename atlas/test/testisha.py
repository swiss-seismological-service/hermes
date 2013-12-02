# -*- encoding: utf-8 -*-
"""
Unit test for the ISHA model package

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from PyQt4 import QtCore
from mock import MagicMock, Mock
from datetime import datetime, timedelta
from model.seismicevent import SeismicEvent
from model.location import Location
from isha.control import ModelController
from isha.common import RunData, Model
from isha.rj import Rj


class MockIshaModel(Model):
    """
    Mock ISHA Model that the model_controller under test controls. Does
    nothing except emitting the finished signal.

    """

    def run(self):
        super(MockIshaModel, self).run()
        self.finished.emit()


class ModelControllerTest(unittest.TestCase):

    def setUp(self):
        """
        We need to setup a QCoreApplication because the QThread stuff expects
        an event loop to be present. We never start the event loop however and
        thus need to process events manually.

        """
        self.app = QtCore.QCoreApplication([])
        self.mock_model = MockIshaModel()
        self.model_controller = ModelController(self.mock_model)

    def test_initialization(self):
        """ Make sure the model is not associated with the main thread """
        this_thread = QtCore.QThread.currentThread()
        self.assertNotEqual(this_thread, self.mock_model.thread())

    def test_start_finish(self):
        """ Check if the model starts and terminates as expected """
        finished_slot = MagicMock()
        self.mock_model.finished.connect(finished_slot)
        dummy_run_data = RunData()
        self.model_controller.start_forecast(dummy_run_data)
        # wait until the model thread emits its signals
        while self.app.hasPendingEvents() is False:
            pass
        self.app.processEvents()
        finished_slot.assert_called_once_with()


class RjTest(unittest.TestCase):

    def setUp(self):
        self.app = QtCore.QCoreApplication([])
        self.model = Rj(a=-1.6, b=1.0, p=1.2, c=0.05)
        self.on_finished = Mock()
        self.model.finished.connect(self.on_finished)

    def create_run_data(self, num_events):
        """
        Creates and returns a run_data structure for *num_events* events. The
        events are spaced by 1 hour, everything else is fixed (see code).

        """
        now = datetime.now()
        shocks = []
        for i in range(num_events):
            location = Location(7.5, 47.5, 0)
            mw = 5.5
            t_event = now - timedelta(hours=i)
            main_shock = SeismicEvent(t_event, mw, location)
            shocks.append(main_shock)

        run_data = RunData()
        run_data.seismic_events = shocks
        run_data.forecast_mag_range = (5.0, 7.0)
        run_data.forecast_times = [now]
        run_data.t_bin = 6.0
        return run_data

    def single_event_test(self):
        """ Test the forecast based on a single event """
        run_data = self.create_run_data(num_events=1)

        # Run the model
        self.model.prepare_run(run_data)
        self.model.run()

        # Deliver signals manually and check if the 'finished' signal has been
        # emitted as expected
        self.app.processEvents()
        self.on_finished.assert_called_once_with(self.model)

        # Compare the result with a precomputed known result for this case
        rate, prob = self.model.run_results[0]
        self.assertAlmostEqual(rate, 0.442, delta=0.001)
        self.assertAlmostEqual(prob, 0.357, delta=0.001)

    def multiple_event_test(self):
        """
        Test the forecast for multiple time bins based on multiple events

        """
        run_data = self.create_run_data(num_events=2)
        t_forecast = run_data.forecast_times[0]
        run_data.forecast_times.append(t_forecast + timedelta(hours=6))

        # Run the model
        self.model.prepare_run(run_data)
        self.model.run()

        # Deliver signals manually and check if the 'finished' signal has been
        # emitted as expected
        self.app.processEvents()
        self.on_finished.assert_called_once_with(self.model)

        # Compare the result with a precomputed known result for this case
        precomputed = [(0.564, 0.431), (0.066, 0.064)]
        for computed, expected in zip(self.model.run_results, precomputed):
            self.assertAlmostEqual(computed[0], expected[0], delta=0.001)
            self.assertAlmostEqual(computed[1], expected[1], delta=0.001)

    def future_event_test(self):
        """
        Test if events occuring after the forecast time are ignored as expected

        """
        run_data = self.create_run_data(2)

        # move the forecast window back to the first event, so the second
        # event should be ignored
        run_data.forecast_times[0] -= timedelta(hours=1)

        # Run the model
        self.model.prepare_run(run_data)
        self.model.run()

        # Deliver signals manually and check if the 'finished' signal has been
        # emitted as expected
        self.app.processEvents()
        self.on_finished.assert_called_once_with(self.model)

        # Compare the result with a precomputed known result for this case
        rate, prob = self.model.run_results[0]
        self.assertAlmostEqual(rate, 0.442, delta=0.001)
        self.assertAlmostEqual(prob, 0.357, delta=0.001)



if __name__ == '__main__':
    unittest.main()
