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
from domainmodel.hydraulicevent import HydraulicEvent
from domainmodel.injectionwell import InjectionWell
from domainmodel.location import Location
from isha.shapiro import Shapiro
from isha.common import ModelInput

from ctypes import *
from os.path import join

class ShapiroTest(unittest.TestCase):

    def setUp(self):
        self.app = QtCore.QCoreApplication([])
        self.model = Shapiro()
        self.model.finished.connect(self.on_finished)
        self.run_results = None

    def on_finished(self, run_results):
        self.run_results = run_results

    def create_model_input(self, num_events):
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

        hydraulic_event = HydraulicEvent(t_event, 100, 100, 10, 10)

        model_input = ModelInput(now)
        model_input.seismic_events = shocks
        model_input.hydraulic_events = [hydraulic_event]
        model_input.forecast_mag_range = (5.0, 7.0)
        model_input.forecast_times = [now]
        model_input.injection_well = InjectionWell(4000, 47.5, 7.5)
        model_input.t_bin = 6.0
        model_input.mc = 0.9
        return model_input

    def test_two_events(self):
        """ Test the basic forecast based on two events """
        model_input = self.create_model_input(num_events=2)
        # Run the model
        self.model.prepare_run(model_input)
        self.model.run()

        # Deliver signals manually and check if the 'finished' signal has been
        # emitted as expected
        self.app.processEvents()
        self.assertIsNotNone(self.run_results)

        # Compare the result with a precomputed known result for this case
        print 'shapiro returns ' + str(self.run_results)

if __name__ == '__main__':
    unittest.main()

