# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from PyQt4 import QtCore
from datetime import datetime, timedelta
from domainmodel.seismicevent import SeismicEvent
from domainmodel.location import Location
from isha.shapiro import Shapiro
from isha.common import RunInput

from ctypes import *
from os.path import join

class ShapiroTest(unittest.TestCase):

    def setUp(self):
        '''
        self.app = QtCore.QCoreApplication([])
        self.model = Shapiro()
        self.model.finished.connect(self.on_finished)
        self.run_results = None
        '''
        pass

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
            location = Location(7.5, 47.5, 0)
            mw = 5.5
            t_event = now - timedelta(hours=i)
            main_shock = SeismicEvent(t_event, mw, location)
            shocks.append(main_shock)

        run_data = RunInput(now)
        run_data.seismic_events = shocks
        run_data.forecast_mag_range = (5.0, 7.0)
        run_data.forecast_times = [now]
        run_data.t_bin = 6.0
        return run_data

    def test_dummy(self):
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
        print 'shapiro returns ' + str(self.run_results)

    def test_x(self):
        matlab_root = '/Applications/MATLAB_R2013a.app'
        engine = CDLL(join(matlab_root, 'bin', 'maci64', 'libeng.dylib'))
        mx = CDLL(join(matlab_root, 'bin', 'maci64', 'libmx.dylib'))

        engine.engOpen.restype = c_void_p
        ep = engine.engOpen(c_char_p('matlab -nodisplay'))

        print 'engine pointer: {:#x}'.format(ep)
        print str(ep)

        engine.engEvalString.argtypes = [c_void_p, c_char_p]
        engine.engEvalString(ep, "D = 3 - 2;")

if __name__ == '__main__':
    unittest.main()

