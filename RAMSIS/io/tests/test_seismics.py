# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Testing facilities for seismic data import.
"""

import datetime
import os
import unittest

import requests

from unittest import mock

from ramsis.datamodel.status import Status  # noqa
from ramsis.datamodel.seismicity import SeismicityModel  # noqa
from ramsis.datamodel.forecast import Forecast  # noqa
from ramsis.datamodel.seismics import SeismicObservationCatalog, SeismicEvent  # noqa
from ramsis.datamodel.well import InjectionWell  # noqa
from ramsis.datamodel.hydraulics import Hydraulics, InjectionPlan  # noqa
from ramsis.datamodel.settings import ProjectSettings  # noqa
from ramsis.datamodel.project import Project  # noqa

from RAMSIS.io.seismics import (QuakeMLObservationCatalogDeserializer,
                                QuakeMLCatalogSerializer)
from RAMSIS.io.utils import binary_request


RAMSIS_PROJ = ("+proj=utm +zone=32N +ellps=WGS84 +datum=WGS84 +units=m "
               "+x_0=0.0 +y_0=0.0 +no_defs")
WGS84_PROJ = "epsg:4326"
REFERENCE_X = 681922
REFERENCE_Y = 1179229


def _read(path):
    """
    Utility method reading testing resources from a file.
    """
    with open(path, 'rb') as ifd:
        retval = ifd.read()

    return retval.strip()


class QuakeMLObservationCatalogDeserializerTestCase(unittest.TestCase):
    """
    Test for :py:class:`RAMSIS.io.seismics.QuakeMLObservationCatalogDeserializer` class.
    """
    PATH_RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'resources')

    def test_with_ifs(self):
        deserializer = QuakeMLObservationCatalogDeserializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_to_local_coords')

        with open(os.path.join(self.PATH_RESOURCES,
                               'cat-00.qml'), 'rb') as ifs:
            cat = deserializer.load(ifs)

        self.assertEqual(len(cat), 2)

        events = sorted(cat)

        e_0 = events[0]
        self.assertEqual(e_0.datetime_value,
                         datetime.datetime(2011, 2, 14, 12, 43, 12, 980000))
        self.assertEqual(e_0.magnitude_value, 4.4)

        self.assertEqual(e_0.x_value, 4807981.415790671)
        self.assertEqual(e_0.y_value, -44215.12188589969)
        self.assertEqual(e_0.z_value, -4100.0)

        e_1 = events[1]
        self.assertEqual(e_1.datetime_value,
                         datetime.datetime(2011, 9, 8, 19, 2, 51, 10000))
        self.assertEqual(e_1.magnitude_value, 4.5)
        self.assertEqual(e_1.x_value, 5031237.042248942)
        self.assertEqual(e_1.y_value, -246331.15090589435)
        self.assertEqual(e_1.z_value, -10300.0)

    def test_with_bytes(self):
        deserializer = QuakeMLObservationCatalogDeserializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_to_local_coords')

        cat = deserializer.loads(
            _read(os.path.join(self.PATH_RESOURCES, 'cat-00.qml')))

        self.assertEqual(len(cat), 2)

        events = sorted(cat)

        e_0 = events[0]
        self.assertEqual(e_0.datetime_value,
                         datetime.datetime(2011, 2, 14, 12, 43, 12, 980000))
        self.assertEqual(e_0.x_value, 4807981.415790671)
        self.assertEqual(e_0.y_value, -44215.12188589969)
        self.assertEqual(e_0.z_value, -4100.0)

        e_1 = events[1]
        self.assertEqual(e_1.datetime_value,
                         datetime.datetime(2011, 9, 8, 19, 2, 51, 10000))
        self.assertEqual(e_1.magnitude_value, 4.5)
        self.assertEqual(e_1.x_value, 5031237.042248942)
        self.assertEqual(e_1.y_value, -246331.15090589435)
        self.assertEqual(e_1.z_value, -10300.0)

    @mock.patch('requests.get')
    def test_with_binary_request(self, mock_req):

        def create_mock_resp():
            m = mock.MagicMock()
            p = mock.PropertyMock(return_value=200)
            type(m).status_code = p

            p = mock.PropertyMock(
                return_value=_read(os.path.join(self.PATH_RESOURCES,
                                   'cat-00.qml')))
            type(m).content = p

            return m

        mock_req.return_value = create_mock_resp()

        url = "http://foo.bar.com/fdsnws/event/1/query"
        req_params = {
            'starttime': '2019-01-01T00:00:00',
            'endtime': '2020-01-01T00:00:00',
            'format': 'xml',
            'magnitudetype': 'ML,Mc,MS,Mw', }

        deserializer = QuakeMLObservationCatalogDeserializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_to_local_coords')

        with binary_request(requests.get, url, req_params) as ifs:
            cat = deserializer.load(ifs)

        self.assertEqual(len(cat), 2)

        events = sorted(cat)

        e_0 = events[0]
        self.assertEqual(e_0.datetime_value,
                         datetime.datetime(2011, 2, 14, 12, 43, 12, 980000))
        self.assertEqual(e_0.x_value, 4807981.415790671)
        self.assertEqual(e_0.y_value, -44215.12188589969)
        self.assertEqual(e_0.z_value, -4100.0)

        e_1 = events[1]
        self.assertEqual(e_1.datetime_value,
                         datetime.datetime(2011, 9, 8, 19, 2, 51, 10000))
        self.assertEqual(e_1.magnitude_value, 4.5)
        self.assertEqual(e_1.x_value, 5031237.042248942)
        self.assertEqual(e_1.y_value, -246331.15090589435)
        self.assertEqual(e_1.z_value, -10300.0)


class QuakeMLCatalogSerializerTestCase(unittest.TestCase):
    """
    Test for :py:class:`RAMSIS.io.seismics.QuakeMLCatalogSerializer` class.
    """
    PATH_RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'resources')

    def test_dump_quakeml(self):

        reference_result = _read(
            os.path.join(self.PATH_RESOURCES, 'cat-01.qml')).decode('utf-8')

        event_0 = _read(os.path.join(self.PATH_RESOURCES, 'e-00.qmlevent'))
        event_1 = _read(os.path.join(self.PATH_RESOURCES, 'e-01.qmlevent'))
        event_2 = _read(os.path.join(self.PATH_RESOURCES, 'e-02.qmlevent'))

        events = [SeismicEvent(quakeml=event_0),
                  SeismicEvent(quakeml=event_1),
                  SeismicEvent(quakeml=event_2)]

        catalog = SeismicObservationCatalog(events=events)

        result = QuakeMLCatalogSerializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_from_local_coords').\
            dumps(catalog)
        self.assertEqual(result, reference_result)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(
        unittest.makeSuite(QuakeMLObservationCatalogDeserializerTestCase, 'test'))
    suite.addTest(
        unittest.makeSuite(QuakeMLCatalogSerializerTestCase, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
