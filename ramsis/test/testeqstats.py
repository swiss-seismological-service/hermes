# -*- encoding: utf-8 -*-
"""
Short Description

Long Description

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from datetime import datetime, timedelta
from core.eqstats import SeismicRateHistory


class RateComputationTest(unittest.TestCase):
    """ Tests EQ _rates computations """

    def setUp(self):
        """
        Create five events spaced by one hour starting on Nov. 27 2013 at 09:15

        """
        start = datetime(2013, 11, 27, 9, 15)
        dt = timedelta(hours=1)
        self.magnitudes = [4, 5.1, 5, 3.8, 2.6]
        self.times = [start + i * dt for i in range(len(self.magnitudes))]

    def test_exact_range(self):
        """ Test rate computation for the exact t/M range of the events """
        t_max = max(self.times)
        dt = max(self.times) - min(self.times)

        rate_history = SeismicRateHistory()
        rate_history.t_bin = dt
        rates = rate_history.compute_and_add(self.magnitudes,
                                             self.times,
                                             [t_max])
        self.assertEqual(rates[0].rate, 1.25)

    def test_one_range(self):
        """ Test rate computation for a larger t_range """
        t_max = datetime(2013, 11, 27, 14)
        dt = t_max - datetime(2013, 11, 27, 9)

        rate_history = SeismicRateHistory()
        rate_history.t_bin = dt
        rates = rate_history.compute_and_add(self.magnitudes,
                                             self.times,
                                             [t_max])
        self.assertEqual(rates[0].rate, 1)

    def test_multiple_bins(self):
        """ Test multiple t bins """
        start = datetime(2013, 11, 27, 9)
        dt = timedelta(hours=3)
        t_range = [start + i * dt for i in range(1, 3)]
        rate_history = SeismicRateHistory()
        rate_history.t_bin = dt
        rates = rate_history.compute_and_add(self.magnitudes,
                                             self.times,
                                             t_range)

        # The first time bin has 1 event
        self.assertEqual(rates[0].rate, 1)
        # The second time bin has 2 events
        self.assertEqual(rates[1].rate, 2.0 / 3)

    def test_lookup_and_clear(self):
        """ Test rate lookups and clearing of history """
        t_max = max(self.times)
        dt = max(self.times) - min(self.times)

        rate_history = SeismicRateHistory()
        rate_history.t_bin = dt
        rate_history.compute_and_add(self.magnitudes,
                                     self.times,
                                     [t_max])

        rate = rate_history.lookup_rate(t_max)
        self.assertEqual(rate.rate, 1.25)
        rate_history.clear()
        self.assertEqual(rate_history.rates, [])
        self.assertEqual(rate_history.times, [])


if __name__ == '__main__':
    unittest.main()
