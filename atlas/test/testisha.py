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

    def test_single_event(self):
        """ Test the forecast based on a single event """
        rj = Rj(a=-1.6, b=1.0, p=1.2, c=0.05)

        # Prepare main shock
        location = Location(7.5, 47.5, 0)
        t_event = datetime.now()
        mw = 5.5
        main_shock = SeismicEvent(t_event, mw, location)

        # Prepare model to run a forecast for the expected rate in the first 12h
        # following the event
        run_data = RunData()
        run_data.seismic_events = [main_shock]
        run_data.forecast_mag_range = (5.0, 7.0)
        run_data.forecast_times = [t_event]
        run_data.t_bin = 12.0

        # Run the model
        on_finished = Mock()
        rj.finished.connect(on_finished)
        rj.prepare_run(run_data)
        rj.run()

        # Deliver signals manually and check if the 'finished' signal has been
        # emitted as expected
        self.app.processEvents()
        on_finished.assert_called_once_with()

        # Compare the result with a precomputed known result for this case
        rate, prob = rj.run_results[0]
        self.assertAlmostEqual(rate, 0.476, delta=0.001)
        self.assertAlmostEqual(prob, 0.379, delta=0.001)

    def multiple_event_test(self):
        """
        Test the forecast for multiple time bins based on multiple events

        """
        rj = Rj(a=-1.6, b=1.0, p=1.2, c=0.05)
        now = datetime.now()

        # Prepare main shock
        shocks = []
        for i in range(2):
            location = Location(7.5, 47.5, 0)
            mw = 5.5
            t_event = now - timedelta(hours=i)
            main_shock = SeismicEvent(t_event, mw, location)
            shocks.append(main_shock)

        # Prepare model to run a forecast for the expected rate in the first 12h
        # following the event
        run_data = RunData()
        run_data.seismic_events = shocks
        run_data.forecast_mag_range = (5.0, 7.0)
        t_last_shock = shocks[0].date_time
        run_data.forecast_times = [t_last_shock,
                                   t_last_shock + timedelta(hours=6)]
        run_data.t_bin = 6.0

        # Run the model
        on_finished = Mock()
        rj.finished.connect(on_finished)
        rj.prepare_run(run_data)
        rj.run()

        # Deliver signals manually and check if the 'finished' signal has been
        # emitted as expected
        self.app.processEvents()
        on_finished.assert_called_once_with()

        # Compare the result with a precomputed known result for this case
        precomputed = [(0.564, 0.431), (0.066, 0.064)]
        for computed, expected in zip(rj.run_results, precomputed):
            self.assertAlmostEqual(computed[0], expected[0], delta=0.001)
            self.assertAlmostEqual(computed[1], expected[1], delta=0.001)



if __name__ == '__main__':
    unittest.main()
