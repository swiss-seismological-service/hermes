# -*- encoding: utf-8 -*-
"""
Short Description

Long Description

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from datetime import datetime, timedelta

from PyQt4 import QtCore

from data.seismicevent import SeismicEvent
from data.geometry import Point
from core.ismodels.rj import Rj
from core.ismodels.common import ModelInput


class TestRj(unittest.TestCase):

    def setUp(self):
        self.app = QtCore.QCoreApplication([])
        self.model = Rj(a=-1.6, b=1.0, p=1.2, c=0.05)
        self.model.finished.connect(self.on_finished)
        self.run_results = None

    def on_finished(self, run_results):
        self.run_results = run_results

    def create_run_data(self, num_events):
        """
        Creates and returns a run_data structure for *num_events* events. The
        events are spaced by 1 hour, everything else is fixed (see code).

        """
        now = datetime.now()
        shocks = []
        for i in range(num_events):
            location = Point(10, 100, 2000)
            mw = 5.5
            t_event = now - timedelta(hours=i)
            main_shock = SeismicEvent(t_event, mw, location)
            shocks.append(main_shock)

        run_data = ModelInput(now)
        run_data.seismic_events = shocks
        run_data.forecast_mag_range = (5.0, 7.0)
        run_data.forecast_times = [now]
        run_data.t_bin = 6.0
        return run_data

    def test_single_event(self):
        """ Test the forecast based on a single event """
        run_data = self.create_run_data(num_events=1)

        # Run the model
        self.model.prepare_run(run_data)
        self.model.run()

        # Deliver signals manually and check if the 'finished' signal has been
        # emitted as expected
        self.app.processEvents()
        self.assertIsNotNone(self.run_results)

        # Compare the result with a precomputed known result for this case
        rate = self.run_results.rates[0]
        prob = self.run_results.probabilities[0]
        self.assertAlmostEqual(rate, 0.442, delta=0.001)
        self.assertAlmostEqual(prob, 0.357, delta=0.001)

    def test_multiple_events(self):
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
        self.assertIsNotNone(self.run_results)

        # Compare the result with a precomputed known result for this case
        expected_rates = [0.564, 0.066]
        expected_probs = [0.431, 0.064]
        for comp, ex in zip(self.run_results.rates, expected_rates):
            self.assertAlmostEqual(comp, ex, delta=0.001)
        for comp, ex in zip(self.run_results.probabilities, expected_probs):
            self.assertAlmostEqual(comp, ex, delta=0.001)

    def test_ignore_future_events(self):
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
        self.assertIsNotNone(self.run_results)

        # Compare the result with a precomputed known result for this case
        rate = self.run_results.rates[0]
        prob = self.run_results.probabilities[0]
        self.assertAlmostEqual(rate, 0.442, delta=0.001)
        self.assertAlmostEqual(prob, 0.357, delta=0.001)


if __name__ == '__main__':
    unittest.main()
