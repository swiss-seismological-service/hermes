# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from datetime import datetime, timedelta
import eqstats


class RateComputationTest(unittest.TestCase):
    """ Tests EQ rates computations """

    def setUp(self):
        """
        Create five events spaced by one hour starting on Nov. 27 2013 at 09:15

        """
        start = datetime(2013, 11, 27, 9, 15)
        dt = timedelta(hours=1)
        self.magnitudes = [4, 5.1, 5, 3.8, 2.6]
        self.times = [start + i*dt for i in range(len(self.magnitudes))]

    def test_exact_range(self):
        """ Test rate computation for the exact t/M range of the events"""
        t_range = [min(self.times), max(self.times)]
        m_range = [min(self.magnitudes), max(self.magnitudes)]

        rates = eqstats.compute_seismic_rates(self.magnitudes, self.times,
                                              t_range, m_range)
        self.assertEqual(rates[0][0], 1.25)

    def test_one_range(self):
        """ Test rate computation for a larger t_range """
        t_range = [datetime(2013, 11, 27, 9), datetime(2013, 11, 27, 14)]
        m_range = [min(self.magnitudes), max(self.magnitudes)]

        rates = eqstats.compute_seismic_rates(self.magnitudes, self.times,
                                              t_range, m_range)
        self.assertEqual(rates[0][0], 1)

    def test_multiple_bins(self):
        """ Test multiple t and M bins """
        start = datetime(2013, 11, 27, 9)
        t_range = [start + i * timedelta(hours=3) for i in range(3)]
        m_range = [2.5, 4, 5.1]
        rates = eqstats.compute_seismic_rates(self.magnitudes, self.times,
                                              t_range, m_range)
        # The first time bin has 0 events < M4 and 3 events >= M4
        self.assertListEqual(rates[0], [0, 1])
        # The second time bin has 2 events < M4 and 0 events >= M4
        self.assertListEqual(rates[1], [2.0/3, 0.0])



if __name__ == '__main__':
    unittest.main()
