# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Testing facilities for borehole/hydraulics data import.
"""

import datetime
import json
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
from RAMSIS.io.utils import (binary_request)


RAMSIS_PROJ = ("+proj=utm +zone=32N +ellps=WGS84 +datum=WGS84 i"
               "+units=m +x_0=0.0 +y_0=0.0 +no_defs")
WGS84_PROJ = 4326
REFERENCE_X = 681922
REFERENCE_Y = 1179229


class HYDWSBoreholeHydraulicsDeserializerTestCase(unittest.TestCase):
    """
    Test for the
    :py:class:`RAMSIS.io.hydraulics.HYDWSBoreholeHydraulicsDeserializer` class.
    """
    PATH_RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'resources')
    maxDiff = None

    def test_with_ifs(self):
        deserializer = HYDWSBoreholeHydraulicsDeserializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_to_local_coords')

        with open(os.path.join(self.PATH_RESOURCES, 'hyd.json'), 'rb') as ifs:
            bh = deserializer.load(ifs)

        self.assertEqual(len(bh.sections), 1)
        self.assertEqual(
            bh.publicid,
            'smi:ch.ethz.sed/bh/11111111-e4a0-4692-bf29-33b5591eb798')

        bh_section = bh.sections[0]
        # borehole section coordinates
        # The location of the borehole should be at the
        # reference point.
        self.assertEqual(int(bh_section.topx_value), 0)
        self.assertEqual(int(bh_section.topy_value), 0)
        self.assertEqual(int(bh_section.topz_value), 100)
        self.assertEqual(int(bh_section.bottomx_value), 0)
        self.assertEqual(int(bh_section.bottomy_value), 0)
        self.assertEqual(int(bh_section.bottomz_value), -900)
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

        deserializer = HYDWSBoreholeHydraulicsDeserializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_to_local_coords')

        with binary_request(requests.get, url, req_params) as ifs:
            bh = deserializer.load(ifs)

        self.assertEqual(len(bh.sections), 1)
        self.assertEqual(
            bh.publicid,
            'smi:ch.ethz.sed/bh/11111111-e4a0-4692-bf29-33b5591eb798')

        bh_section = bh.sections[0]
        # borehole section coordinates
        # The location of the borehole should be at the
        # reference point.
        self.assertEqual(int(bh_section.topx_value), 0)
        self.assertEqual(int(bh_section.topy_value), 0)
        self.assertEqual(int(bh_section.topz_value), 100)
        self.assertEqual(int(bh_section.bottomx_value), 0)
        self.assertEqual(int(bh_section.bottomy_value), 0)
        self.assertEqual(int(bh_section.bottomz_value), -900)
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

    def test_import_plan(self):
        deserializer = HYDWSBoreholeHydraulicsDeserializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_to_local_coords',
            plan=True)

        with open(os.path.join(self.PATH_RESOURCES, 'hyd.json'), 'rb') as ifs:
            bh = deserializer.load(ifs)

        self.assertEqual(len(bh.sections), 1)
        self.assertEqual(
            bh.publicid,
            'smi:ch.ethz.sed/bh/11111111-e4a0-4692-bf29-33b5591eb798')

        bh_section = bh.sections[0]
        # borehole section coordinates
        # The location of the borehole should be at the
        # reference point.
        self.assertEqual(int(bh_section.topx_value), 0)
        self.assertEqual(int(bh_section.topy_value), 0)
        self.assertEqual(int(bh_section.topz_value), 100)
        self.assertEqual(int(bh_section.bottomx_value), 0)
        self.assertEqual(int(bh_section.bottomy_value), 0)
        self.assertEqual(int(bh_section.bottomz_value), -900)
        # additional borehole section attributes
        self.assertEqual(len(bh_section.injectionplan.samples), 2)
        self.assertEqual(
            bh_section.publicid,
            'smi:ch.ethz.sed/bh/section/11111111-8d89-4f13-95e7-526ade73cc8b')
        self.assertEqual(bh_section.holediameter_value, 0.3)

        # briefly validate samples
        s0 = bh_section.injectionplan.samples[0]
        self.assertEqual(s0.datetime_value,
                         datetime.datetime(2019, 5, 3, 13, 27, 9, 117623))
        s1 = bh_section.injectionplan.samples[1]
        self.assertEqual(s1.datetime_value,
                         datetime.datetime(2019, 5, 3, 15, 27, 9, 117623))

    def test_section_without_samples(self):

        deserializer = HYDWSBoreholeHydraulicsDeserializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_to_local_coords')

        with open(os.path.join(self.PATH_RESOURCES,
                               'hyd-no-samples.json'), 'rb') as ifs:
            bh = deserializer.load(ifs)

        bh_section = bh.sections[0]
        # borehole section coordinates
        # The location of the borehole should be at the
        # reference point.
        self.assertEqual(int(bh_section.topx_value), 0)
        self.assertEqual(int(bh_section.topy_value), 0)
        self.assertEqual(int(bh_section.topz_value), 100)
        self.assertEqual(int(bh_section.bottomx_value), 0)
        self.assertEqual(int(bh_section.bottomy_value), 0)
        self.assertEqual(int(bh_section.bottomz_value), -900)
        # additional borehole section attributes
        self.assertEqual(
            bh_section.publicid,
            'smi:ch.ethz.sed/bh/section/11111111-8d89-4f13-95e7-526ade73cc8b')
        self.assertEqual(bh_section.holediameter_value, 0.3)


class HYDWSBoreholeHydraulicsSerializerTestCase(unittest.TestCase):
    """
    Test for the
    :py:class:`RAMSIS.io.hydraulics.HYDWSBoreholeHydraulicsSerializer` class.
    """

    maxDiff = None

    def test_well_only(self):
        reference_result = {
            'altitude': {'value': 0.0},
            'publicid': ('smi:ch.ethz.sed/bh/'
                         '11111111-e4a0-4692-bf29-33b5591eb798'),
            'sections': [{
                'toplongitude': {'value': 10.663205540045357},
                'toplatitude': {'value': 10.663204912654692},
                'topdepth': {'value': 0.0},
                'bottomlongitude': {'value': 10.663205540045357},
                'bottomlatitude': {'value': 10.663204912654692},
                'bottomdepth': {'value': 1000.0},
                'holediameter': {'value': 0.3},
                'topclosed': False,
                'bottomclosed': False,
                'publicid': ('smi:ch.ethz.sed/bh/section/'
                             '11111111-8d89-4f13-95e7-526ade73cc8b')}]}

        sec = WellSection(
            publicid=('smi:ch.ethz.sed/bh/section/'
                      '11111111-8d89-4f13-95e7-526ade73cc8b'),
            topx_value=0.0,
            topy_value=0.0,
            topz_value=0.0,
            bottomx_value=0.0,
            bottomy_value=0.0,
            bottomz_value=-1000.0,
            holediameter_value=0.3,
            topclosed=False,
            bottomclosed=False,
            hydraulics=None)
        bh = InjectionWell(
            publicid='smi:ch.ethz.sed/bh/11111111-e4a0-4692-bf29-33b5591eb798',
            altitude_value=0.0,
            sections=[sec, ])
        serializer = HYDWSBoreholeHydraulicsSerializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_from_local_coords')

        serialized_result = json.loads(serializer.dumps(bh))
        self.assertEqual(serialized_result, reference_result)

    def test_with_hydraulics(self):
        self.maxDiff = None
        # XXX(damb): Depending on the coordinate transformation used the
        # results might vary.
        reference_result = {
            'altitude': {'value': 0.0},
            'publicid': ('smi:ch.ethz.sed/bh/'
                         '11111111-e4a0-4692-bf29-33b5591eb798'),
            'sections': [{
                'toplongitude': {'value': 10.663205540045357},
                'toplatitude': {'value': 10.663204912654692},
                'topdepth': {'value': 0.0},
                'bottomlongitude': {'value': 10.663205540045357},
                'bottomlatitude': {'value': 10.663204912654692},
                'bottomdepth': {'value': 1000.0},
                'holediameter': {'value': 0.3},
                'topclosed': False,
                'bottomclosed': False,
                'publicid': ('smi:ch.ethz.sed/bh/section/'
                             '11111111-8d89-4f13-95e7-526ade73cc8b'),

                'hydraulics': [
                    {'datetime':
                        {'value': '2019-05-03T13:27:09.117623'}},
                    {'datetime':
                        {'value': '2019-05-03T15:27:09.117623'}}]}]}
        s0 = HydraulicSample(
            datetime_value=datetime.datetime(2019, 5, 3, 13, 27, 9, 117623))
        s1 = HydraulicSample(
            datetime_value=datetime.datetime(2019, 5, 3, 15, 27, 9, 117623))

        hyd = Hydraulics(samples=[s0, s1])

        sec = WellSection(
            publicid=('smi:ch.ethz.sed/bh/section/'
                      '11111111-8d89-4f13-95e7-526ade73cc8b'),
            topx_value=0,
            topy_value=0,
            topz_value=0,
            bottomx_value=0,
            bottomy_value=0,
            bottomz_value=-1000,
            holediameter_value=0.3,
            topclosed=False,
            bottomclosed=False,
            hydraulics=hyd)

        bh = InjectionWell(
            publicid='smi:ch.ethz.sed/bh/11111111-e4a0-4692-bf29-33b5591eb798',
            altitude_value=0.0,
            sections=[sec])

        serializer = HYDWSBoreholeHydraulicsSerializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_from_local_coords')
        serialized_result = json.loads(serializer.dumps(bh))
        self.assertEqual(serialized_result, reference_result)

    def test_with_injectionplan(self):
        # XXX(damb): Depending on the coordinate transformation used the
        # results might vary.
        reference_result = {
            'altitude': {'value': 0.0},
            'publicid': ('smi:ch.ethz.sed/bh/'
                         '11111111-e4a0-4692-bf29-33b5591eb798'),
            'sections': [{
                'toplongitude': {'value': 10.663205540045357},
                'toplatitude': {'value': 10.663204912654692},
                'topdepth': {'value': 0.0},
                'bottomlongitude': {'value': 10.663205540045357},
                'bottomlatitude': {'value': 10.663204912654692},
                'bottomdepth': {'value': 1000.0},
                'holediameter': {'value': 0.3},
                'topclosed': False,
                'bottomclosed': False,
                'publicid': ('smi:ch.ethz.sed/bh/section/'
                             '11111111-8d89-4f13-95e7-526ade73cc8b'),

                'hydraulics': [
                    {'datetime':
                        {'value': '2019-05-03T13:27:09.117623'}},
                    {'datetime':
                        {'value': '2019-05-03T15:27:09.117623'}}]}]}

        s0 = HydraulicSample(
            datetime_value=datetime.datetime(2019, 5, 3, 13, 27, 9, 117623))
        s1 = HydraulicSample(
            datetime_value=datetime.datetime(2019, 5, 3, 15, 27, 9, 117623))

        plan = InjectionPlan(samples=[s0, s1])

        sec = WellSection(
            publicid=('smi:ch.ethz.sed/bh/section/'
                      '11111111-8d89-4f13-95e7-526ade73cc8b'),
            topx_value=0,
            topy_value=0,
            topz_value=0,
            bottomx_value=0,
            bottomy_value=0,
            bottomz_value=-1000,
            holediameter_value=0.3,
            topclosed=False,
            bottomclosed=False,
            injectionplan=plan)

        bh = InjectionWell(
            publicid='smi:ch.ethz.sed/bh/11111111-e4a0-4692-bf29-33b5591eb798',
            altitude_value=0.0,
            sections=[sec])

        serializer = HYDWSBoreholeHydraulicsSerializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_from_local_coords',
            plan=True)

        serialized_result = json.loads(serializer.dumps(bh))
        self.assertEqual(serialized_result, reference_result)


class HYDWSBoreholeHydraulicsTransformationTestCase(unittest.TestCase):
    """
    Test for the
    :py:class:`RAMSIS.io.hydraulics.HYDWSBoreholeHydraulicsDeserializer` class.
    """
    PATH_RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'resources')

    def test_with_circular_transformation(self):
        deserializer = HYDWSBoreholeHydraulicsDeserializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_to_local_coords')

        with open(os.path.join(self.PATH_RESOURCES, 'hyd.json'), 'rb') as ifs:
            bh = deserializer.load(ifs)
        with open(os.path.join(self.PATH_RESOURCES, 'hyd.json'), 'r') as ifs:
            reference_result = json.load(ifs)

        serializer = HYDWSBoreholeHydraulicsSerializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_from_local_coords')
        serialized_sec = json.loads(serializer.dumps(bh))['sections'][0]
        expected_sec = reference_result['sections'][0]
        self.assertAlmostEqual(serialized_sec['bottomlatitude']['value'],
                               expected_sec['bottomlatitude']['value'])
        self.assertAlmostEqual(serialized_sec['toplatitude']['value'],
                               expected_sec['toplatitude']['value'])
        self.assertAlmostEqual(serialized_sec['toplongitude']['value'],
                               expected_sec['toplongitude']['value'])
        self.assertAlmostEqual(serialized_sec['bottomlongitude']['value'],
                               expected_sec['bottomlongitude']['value'])
        self.assertAlmostEqual(serialized_sec['topdepth']['value'],
                               expected_sec['topdepth']['value'])
        self.assertAlmostEqual(serialized_sec['bottomdepth']['value'],
                               expected_sec['bottomdepth']['value'])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(
        unittest.makeSuite(
            HYDWSBoreholeHydraulicsDeserializerTestCase, 'test'))
    suite.addTest(
        unittest.makeSuite(HYDWSBoreholeHydraulicsSerializerTestCase, 'test'))
    suite.addTest(
        unittest.makeSuite(HYDWSBoreholeHydraulicsTransformationTestCase,
                           'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
