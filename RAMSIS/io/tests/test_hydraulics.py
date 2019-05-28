# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Testing facilities for borehole/hydraulics data import.
"""

import datetime
import os
import unittest

from unittest import mock

import requests

from ramsis.datamodel.status import Status  # noqa
from ramsis.datamodel.seismicity import SeismicityModel  # noqa
from ramsis.datamodel.forecast import Forecast  # noqa
from ramsis.datamodel.seismics import SeismicCatalog, SeismicEvent  # noqa
from ramsis.datamodel.well import InjectionWell, WellSection  # noqa
from ramsis.datamodel.hydraulics import (Hydraulics, InjectionPlan,  # noqa
                                         HydraulicSample) # noqa
from ramsis.datamodel.settings import ProjectSettings  # noqa
from ramsis.datamodel.project import Project  # noqa

from RAMSIS.io.hydraulics import (HYDWSBoreholeHydraulicsDeserializer,
                                  HYDWSBoreholeHydraulicsSerializer)
from RAMSIS.io.utils import (binary_request, pymap3d_transform_geodetic2ned,
                             pymap3d_transform_ned2geodetic)


class HYDWSBoreholeHydraulicsDeserializerTestCase(unittest.TestCase):
    """
    Test for the
    :py:class:`RAMSIS.io.hydraulics.HYDWSBoreholeHydraulicsDeserializer` class.
    """
    PATH_RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'resources')

    def test_with_ifs(self):
        proj = '+x_0=0 +y_0=0 +z_0=0'
        deserializer = HYDWSBoreholeHydraulicsDeserializer(
            proj=proj, transform_callback=pymap3d_transform_geodetic2ned)

        with open(os.path.join(self.PATH_RESOURCES, 'hyd.json'), 'rb') as ifs:
            bh = deserializer.load(ifs)

        self.assertEqual(len(bh.sections), 1)
        self.assertEqual(
            bh.publicid,
            'smi:ch.ethz.sed/bh/11111111-e4a0-4692-bf29-33b5591eb798')

        bh_section = bh.sections[0]
        # borehole section coordinates
        self.assertEqual(bh_section.toplongitude_value, 1172416.0953340977)
        self.assertEqual(bh_section.toplatitude_value, 1159935.6543754074)
        self.assertEqual(bh_section.topdepth_value, 217669.68585873488)
        self.assertEqual(bh_section.bottomlongitude_value, 1172601.1309198323)
        self.assertEqual(bh_section.bottomlatitude_value, 1160117.4947335268)
        self.assertEqual(bh_section.bottomdepth_value, 216703.92402672302)
        # additional borehole section attributes
        self.assertEqual(len(bh_section.hydraulics.samples), 2)
        self.assertEqual(
            bh_section.publicid,
            'smi:ch.ethz.sed/bh/section/11111111-8d89-4f13-95e7-526ade73cc8b')
        self.assertEqual(bh_section.holediameter_value, 0.3)

        # briefly validate samples
        s0 = bh_section.hydraulics.samples[0]
        self.assertEqual(s0.datetime_value,
                         datetime.datetime(2019, 5, 3, 13, 27, 9, 117623))
        s1 = bh_section.hydraulics.samples[1]
        self.assertEqual(s1.datetime_value,
                         datetime.datetime(2019, 5, 3, 15, 27, 9, 117623))

    @mock.patch('requests.get')
    def test_with_binary_request(self, mock_req):

        def create_mock_resp():
            m = mock.MagicMock()
            p = mock.PropertyMock(return_value=200)
            type(m).status_code = p

            with open(os.path.join(self.PATH_RESOURCES, 'hyd.json'),
                      'rb') as ifs:
                p = mock.PropertyMock(return_value=ifs.read())
                type(m).content = p

            return m

        mock_req.return_value = create_mock_resp()

        url = ("http://foo.bar.com/v1/borehole/"
               "c21pOmNoLmV0aHouc2VkL2JoLzExMTExMTExLWU0YTAtNDY5Mi1iZjI5LTMzY"
               "jU1OTFlYjc5OA==")
        req_params = {
            'starttime': '2019-01-01T00:00:00',
            'endtime': '2020-01-01T00:00:00',
            'format': 'json', }
        proj = '+x_0=0 +y_0=0 +z_0=0'

        deserializer = HYDWSBoreholeHydraulicsDeserializer(
            proj=proj, transform_callback=pymap3d_transform_geodetic2ned)

        with binary_request(requests.get, url, req_params) as ifs:
            bh = deserializer.load(ifs)

        self.assertEqual(len(bh.sections), 1)
        self.assertEqual(
            bh.publicid,
            'smi:ch.ethz.sed/bh/11111111-e4a0-4692-bf29-33b5591eb798')

        bh_section = bh.sections[0]
        # borehole section coordinates
        self.assertEqual(bh_section.toplongitude_value, 1172416.0953340977)
        self.assertEqual(bh_section.toplatitude_value, 1159935.6543754074)
        self.assertEqual(bh_section.topdepth_value, 217669.68585873488)
        self.assertEqual(bh_section.bottomlongitude_value, 1172601.1309198323)
        self.assertEqual(bh_section.bottomlatitude_value, 1160117.4947335268)
        self.assertEqual(bh_section.bottomdepth_value, 216703.92402672302)
        # additional borehole section attributes
        self.assertEqual(len(bh_section.hydraulics.samples), 2)
        self.assertEqual(
            bh_section.publicid,
            'smi:ch.ethz.sed/bh/section/11111111-8d89-4f13-95e7-526ade73cc8b')
        self.assertEqual(bh_section.holediameter_value, 0.3)

        # briefly validate samples
        s0 = bh_section.hydraulics.samples[0]
        self.assertEqual(s0.datetime_value,
                         datetime.datetime(2019, 5, 3, 13, 27, 9, 117623))
        s1 = bh_section.hydraulics.samples[1]
        self.assertEqual(s1.datetime_value,
                         datetime.datetime(2019, 5, 3, 15, 27, 9, 117623))


class HYDWSBoreholeHydraulicsSerializerTestCase(unittest.TestCase):
    """
    Test for the
    :py:class:`RAMSIS.io.hydraulics.HYDWSBoreholeHydraulicsSerializer` class.
    """

    def test_with_hydraulics(self):
        # XXX(damb): Depending on the coordinate transformation used the
        # results might vary.
        reference_result = {
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
                             '11111111-e4a0-4692-bf29-33b5591eb798')}

        s0 = HydraulicSample(
            datetime_value=datetime.datetime(2019, 5, 3, 13, 27, 9, 117623))
        s1 = HydraulicSample(
            datetime_value=datetime.datetime(2019, 5, 3, 15, 27, 9, 117623))

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

        proj = '+x_0=0 +y_0=0 +z_0=0'
        serializer = HYDWSBoreholeHydraulicsSerializer(
            proj=proj, transform_callback=pymap3d_transform_ned2geodetic)

        self.assertEqual(serializer.dump(bh), reference_result)

    def test_with_injectionplan(self):
        # XXX(damb): Depending on the coordinate transformation used the
        # results might vary.
        reference_result = {
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
                             '11111111-e4a0-4692-bf29-33b5591eb798')}

        s0 = HydraulicSample(
            datetime_value=datetime.datetime(2019, 5, 3, 13, 27, 9, 117623))
        s1 = HydraulicSample(
            datetime_value=datetime.datetime(2019, 5, 3, 15, 27, 9, 117623))

        plan = InjectionPlan(samples=[s0, s1])

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
            injectionplan=plan)

        bh = InjectionWell(
            publicid='smi:ch.ethz.sed/bh/11111111-e4a0-4692-bf29-33b5591eb798',
            sections=[sec])

        proj = '+x_0=0 +y_0=0 +z_0=0'
        serializer = HYDWSBoreholeHydraulicsSerializer(
            proj=proj, plan=True,
            transform_callback=pymap3d_transform_ned2geodetic)

        self.assertEqual(serializer.dump(bh), reference_result)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(
        unittest.makeSuite(
            HYDWSBoreholeHydraulicsDeserializerTestCase, 'test'))
    suite.addTest(
        unittest.makeSuite(HYDWSBoreholeHydraulicsSerializerTestCase, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
