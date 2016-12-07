# # -*- encoding: utf-8 -*-
# """
# Test ISHA common module
#
# Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED
#
# """
#
# import unittest
# from datetime import datetime
#
# import core.engine.ismodels.common as common
#
#
# class MockSeismicEvent:
#     data_attrs = ['magnitude', 'date_time']
#
#     def __init__(self, dt):
#         self.date_time = dt
#         self.magnitude = 3
#
#
# class ModelInputTest(unittest.TestCase):
#
#     def test_primitive_rep(self):
#         """
#         Tests the generation of a primitive representation of the run input
#
#         """
#         t0 = datetime(1970, 1, 1, 1)
#         test_input = common.ModelInput(t0)
#         test_input.seismic_events = [MockSeismicEvent(t0),
#                                      MockSeismicEvent(t0)]
#         test_input.hydraulic_events = []
#         test_input.forecast_mag_range = (3, 4)
#         test_input.forecast_times = [t0]
#         test_input.injection_well = None
#         test_input.mc = 0.9
#         test_input.t_bin = 6.0
#         primitive_inputs = {n: a for (n, a) in test_input.primitive_rep()}
#         expected = {
#             't_run': [3600.0],
#             'forecast_mag_range': (3, 4),
#             'seismic_events_magnitude': [3, 3],
#             'seismic_events_date_time': [3600.0, 3600.0],
#             'hydraulic_events': [],
#             'expected_flow': [],
#             'injection_well': [],
#             'forecast_times': [3600.0],
#             't_bin': [6.0],
#             'mc': [0.9]
#         }
#         self.assertEqual(primitive_inputs, expected)
#
#
# if __name__ == '__main__':
#     unittest.main()
