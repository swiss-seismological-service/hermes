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
from ramsis.datamodel.seismics import SeismicCatalog, SeismicEvent  # noqa
from ramsis.datamodel.well import InjectionWell  # noqa
from ramsis.datamodel.hydraulics import Hydraulics, InjectionPlan  # noqa
from ramsis.datamodel.settings import ProjectSettings  # noqa
from ramsis.datamodel.project import Project  # noqa

from RAMSIS.io.seismics import (QuakeMLCatalogDeserializer,
                                QuakeMLCatalogSerializer)
from RAMSIS.io.utils import binary_request, pymap3d_transform_geodetic2ned


def _read(path):
    """
    Utility method reading testing resources from a file.
    """
    with open(path, 'rb') as ifd:
        retval = ifd.read()

    return retval.strip()


class QuakeMLCatalogDeserializerTestCase(unittest.TestCase):
    """
    Test for :py:class:`RAMSIS.io.seismics.QuakeMLCatalogDeserializer` class.
    """
    PATH_RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'resources')

    def test_with_ifs(self):
        proj = '+x_0=0 +y_0=0 +z_0=0'
        deserializer = QuakeMLCatalogDeserializer(
            proj=proj, transform_callback=pymap3d_transform_geodetic2ned)

        with open(os.path.join(self.PATH_RESOURCES,
                               'cat-00.qml'), 'rb') as ifs:
            cat = deserializer.load(ifs)

        self.assertEqual(len(cat), 2)

        events = sorted(cat)

        e_0 = events[0]
        self.assertEqual(e_0.datetime_value,
                         datetime.datetime(2011, 2, 14, 12, 43, 12, 980000))
        self.assertEqual(e_0.magnitude_value, 4.4)
        self.assertEqual(e_0.x_value, 852934.4308659385)
        self.assertEqual(e_0.y_value, 4865438.458302228)
        self.assertEqual(e_0.z_value, 2337337.475712796)

        e_1 = events[1]
        self.assertEqual(e_1.datetime_value,
                         datetime.datetime(2011, 9, 8, 19, 2, 51, 10000))
        self.assertEqual(e_1.magnitude_value, 4.5)
        self.assertEqual(e_1.x_value, 686647.2190603528)
        self.assertEqual(e_1.y_value, 4980141.7949330835)
        self.assertEqual(e_1.z_value, 2436607.0696544466)

    def test_with_bytes(self):
        proj = '+x_0=0 +y_0=0 +z_0=0'
        deserializer = QuakeMLCatalogDeserializer(
            proj=proj, transform_callback=pymap3d_transform_geodetic2ned)

        cat = deserializer.loads(
            _read(os.path.join(self.PATH_RESOURCES, 'cat-00.qml')))

        self.assertEqual(len(cat), 2)

        events = sorted(cat)

        e_0 = events[0]
        self.assertEqual(e_0.datetime_value,
                         datetime.datetime(2011, 2, 14, 12, 43, 12, 980000))
        self.assertEqual(e_0.magnitude_value, 4.4)
        self.assertEqual(e_0.x_value, 852934.4308659385)
        self.assertEqual(e_0.y_value, 4865438.458302228)
        self.assertEqual(e_0.z_value, 2337337.475712796)

        e_1 = events[1]
        self.assertEqual(e_1.datetime_value,
                         datetime.datetime(2011, 9, 8, 19, 2, 51, 10000))
        self.assertEqual(e_1.magnitude_value, 4.5)
        self.assertEqual(e_1.x_value, 686647.2190603528)
        self.assertEqual(e_1.y_value, 4980141.7949330835)
        self.assertEqual(e_1.z_value, 2436607.0696544466)

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

        proj = '+x_0=0 +y_0=0 +z_0=0'
        deserializer = QuakeMLCatalogDeserializer(
            proj=proj,
            transform_callback=pymap3d_transform_geodetic2ned)

        with binary_request(requests.get, url, req_params) as ifs:
            cat = deserializer.load(ifs)

        self.assertEqual(len(cat), 2)

        events = sorted(cat)

        e_0 = events[0]
        self.assertEqual(e_0.datetime_value,
                         datetime.datetime(2011, 2, 14, 12, 43, 12, 980000))
        self.assertEqual(e_0.magnitude_value, 4.4)
        self.assertEqual(e_0.x_value, 852934.4308659385)
        self.assertEqual(e_0.y_value, 4865438.458302228)
        self.assertEqual(e_0.z_value, 2337337.475712796)

        e_1 = events[1]
        self.assertEqual(e_1.datetime_value,
                         datetime.datetime(2011, 9, 8, 19, 2, 51, 10000))
        self.assertEqual(e_1.magnitude_value, 4.5)
        self.assertEqual(e_1.x_value, 686647.2190603528)
        self.assertEqual(e_1.y_value, 4980141.7949330835)

        self.assertEqual(e_1.z_value, 2436607.0696544466)

    def test_no_proj(self):
        deserializer = QuakeMLCatalogDeserializer(proj=None)

        cat = deserializer.loads(
            _read(os.path.join(self.PATH_RESOURCES, 'cat-00.qml')))

        self.assertEqual(len(cat), 2)

        events = sorted(cat)

        e_0 = events[0]
        self.assertEqual(e_0.datetime_value,
                         datetime.datetime(2011, 2, 14, 12, 43, 12, 980000))
        self.assertEqual(e_0.magnitude_value, 4.4)
        self.assertEqual(e_0.x_value, 7.731667)
        self.assertEqual(e_0.y_value, 50.29)
        self.assertEqual(e_0.z_value, 4100.0)

        e_1 = events[1]
        self.assertEqual(e_1.datetime_value,
                         datetime.datetime(2011, 9, 8, 19, 2, 51, 10000))
        self.assertEqual(e_1.magnitude_value, 4.5)
        self.assertEqual(e_1.x_value, 6.211667)
        self.assertEqual(e_1.y_value, 51.64017)
        self.assertEqual(e_1.z_value, 10300.0)


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

        catalog = SeismicCatalog(events=events)

        self.assertEqual(QuakeMLCatalogSerializer().dumps(catalog),
                         reference_result)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(
        unittest.makeSuite(QuakeMLCatalogDeserializerTestCase, 'test'))
    suite.addTest(
        unittest.makeSuite(QuakeMLCatalogSerializerTestCase, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
