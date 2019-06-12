# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Testing facilities for SFM-Worker IO.
"""

import base64
import datetime
import json
import os
import unittest

from ramsis.datamodel.status import Status  # noqa
from ramsis.datamodel.seismicity import SeismicityModel  # noqa
from ramsis.datamodel.forecast import Forecast  # noqa
from ramsis.datamodel.seismics import SeismicCatalog, SeismicEvent  # noqa
from ramsis.datamodel.well import InjectionWell, WellSection  # noqa
from ramsis.datamodel.hydraulics import (Hydraulics, InjectionPlan,  # noqa
                                         HydraulicSample) # noqa
from ramsis.datamodel.settings import ProjectSettings  # noqa
from ramsis.datamodel.project import Project  # noqa

from RAMSIS.io.sfm import SFMWorkerIMessageSerializer
from RAMSIS.io.utils import pymap3d_transform_ned2geodetic


def _read(path):
    """
    Utility method reading testing resources from a file.
    """
    with open(path, 'rb') as ifd:
        retval = ifd.read()

    return retval.strip()


class SFMWorkerIMessageSerializerTestCase(unittest.TestCase):
    """
    Test for :py:class:`RAMSIS.io.sfm.SFMWorkerIMessageSerializer` class.
    """
    PATH_RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'resources')

    def test_dumps_imessage(self):

        reference_catalog = _read(os.path.join(self.PATH_RESOURCES,
                                               'cat-01.qml'))
        reference_catalog = base64.b64encode(
            reference_catalog).decode('utf-8')

        reference_result = {
            'seismic_catalog': {
                'quakeml': reference_catalog},
            'well': {
                'sections': [{
                    'toplongitude': {'value': 10.663207130000002},
                    'toplatitude': {'value': 10.66320713},
                    'topdepth': {'value': 0.0},
                    'bottomlatitude': {'value': 10.66320713},
                    'bottomlongitude': {'value': 10.66320713},
                    'bottomdepth': {'value': 1000.0000000004027},
                    'holediameter': {'value': 0.3},
                    'topclosed': False,
                    'bottomclosed': False,
                    'publicid': ('smi:ch.ethz.sed/bh/section/'
                                 '11111111-8d89-4f13-95e7-526ade73cc8b'),
                    'hydraulics': [
                        {'datetime':
                            {'value': '2019-05-03T13:27:09.117623+00:00'}},
                        {'datetime':
                            {'value': '2019-05-03T15:27:09.117623+00:00'}}]}],
                    'publicid': ('smi:ch.ethz.sed/bh/'
                                 '11111111-e4a0-4692-bf29-33b5591eb798')},
            'scenario': {
                'well': {
                    'sections': [{
                        'toplongitude': {'value': 10.663207130000002},
                        'toplatitude': {'value': 10.66320713},
                        'topdepth': {'value': 0.0},
                        'bottomlatitude': {'value': 10.66320713},
                        'bottomlongitude': {'value': 10.66320713},
                        'bottomdepth': {'value': 1000.0000000004027},
                        'holediameter': {'value': 0.3},
                        'topclosed': False,
                        'bottomclosed': False,
                        'publicid': ('smi:ch.ethz.sed/bh/section/'
                                     '11111111-8d89-4f13-95e7-526ade73cc8b'),
                        'hydraulics': [
                            {'datetime':
                                {'value': '2019-05-03T17:27:09.117623+00:00'}},
                            {'datetime':
                                {'value': ('2019-05-03T'
                                           '19:27:09.117623+00:00')}}]}],
                        'publicid': ('smi:ch.ethz.sed/bh/'
                                     '11111111-e4a0-4692-bf29-33b5591eb798')}},
                'reservoir': {'geom':
                              ('POLYHEDRALSURFACE Z '
                               '(((0 0 0, 0 2 0, 2 2 0, 2 0 0, 0 0 0)),'
                               '((0 0 0, 0 2 0, 0 2 2, 0 0 2, 0 0 0)),'
                               '((0 0 0, 2 0 0, 2 0 2, 0 0 2, 0 0 0)),'
                               '((2 2 2, 2 0 2, 0 0 2, 0 2 2, 2 2 2)),'
                               '((2 2 2, 2 0 2, 2 0 0, 2 2 0, 2 2 2)),'
                               '((2 2 2, 2 2 0, 0 2 0, 0 2 2, 2 2 2)))')}}

        event_0 = _read(os.path.join(self.PATH_RESOURCES, 'e-00.qmlevent'))
        event_1 = _read(os.path.join(self.PATH_RESOURCES, 'e-01.qmlevent'))
        event_2 = _read(os.path.join(self.PATH_RESOURCES, 'e-02.qmlevent'))

        events = [SeismicEvent(quakeml=event_0),
                  SeismicEvent(quakeml=event_1),
                  SeismicEvent(quakeml=event_2)]

        catalog = SeismicCatalog(events=events)

        reservoir = ('POLYHEDRALSURFACE Z '
                     '(((0 0 0, 0 2 0, 2 2 0, 2 0 0, 0 0 0)),'
                     '((0 0 0, 0 2 0, 0 2 2, 0 0 2, 0 0 0)),'
                     '((0 0 0, 2 0 0, 2 0 2, 0 0 2, 0 0 0)),'
                     '((2 2 2, 2 0 2, 0 0 2, 0 2 2, 2 2 2)),'
                     '((2 2 2, 2 0 2, 2 0 0, 2 2 0, 2 2 2)),'
                     '((2 2 2, 2 2 0, 0 2 0, 0 2 2, 2 2 2)))')

        s0 = HydraulicSample(
            datetime_value=datetime.datetime(2019, 5, 3, 13, 27, 9, 117623))
        s1 = HydraulicSample(
            datetime_value=datetime.datetime(2019, 5, 3, 15, 27, 9, 117623))
        s2 = HydraulicSample(
            datetime_value=datetime.datetime(2019, 5, 3, 17, 27, 9, 117623))
        s3 = HydraulicSample(
            datetime_value=datetime.datetime(2019, 5, 3, 19, 27, 9, 117623))

        hyd = Hydraulics(samples=[s0, s1])

        sec = WellSection(
            publicid=('smi:ch.ethz.sed/bh/section/'
                      '11111111-8d89-4f13-95e7-526ade73cc8b'),
            toplongitude_value=1172416.0953340977,
            toplatitude_value=1159935.6543754074,
            topdepth_value=217669.68585873488,
            bottomlongitude_value=1172601.1309198323,
            bottomlatitude_value=1160117.4947335268,
            bottomdepth_value=216703.92402672302,
            holediameter_value=0.3,
            topclosed=False,
            bottomclosed=False,
            hydraulics=hyd)

        bh = InjectionWell(
            publicid='smi:ch.ethz.sed/bh/11111111-e4a0-4692-bf29-33b5591eb798',
            sections=[sec])

        plan = InjectionPlan(samples=[s2, s3])

        sec_scenario = WellSection(
            publicid=('smi:ch.ethz.sed/bh/section/'
                      '11111111-8d89-4f13-95e7-526ade73cc8b'),
            toplongitude_value=1172416.0953340977,
            toplatitude_value=1159935.6543754074,
            topdepth_value=217669.68585873488,
            bottomlongitude_value=1172601.1309198323,
            bottomlatitude_value=1160117.4947335268,
            bottomdepth_value=216703.92402672302,
            holediameter_value=0.3,
            topclosed=False,
            bottomclosed=False,
            injectionplan=plan)

        bh_scenario = InjectionWell(
            publicid='smi:ch.ethz.sed/bh/11111111-e4a0-4692-bf29-33b5591eb798',
            sections=[sec_scenario])

        proj = '+x_0=0 +y_0=0 +z_0=0'
        serializer = SFMWorkerIMessageSerializer(
            proj=proj, transform_callback=pymap3d_transform_ned2geodetic)

        payload = {'seismic_catalog': {'quakeml': catalog},
                   'well': bh,
                   'scenario': {'well': bh_scenario},
                   'reservoir': {'geom': reservoir},
                   'model_parameters': {}}

        self.assertEqual(reference_result,
                         json.loads(serializer.dumps(payload)))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(
        unittest.makeSuite(SFMWorkerIMessageSerializerTestCase, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
