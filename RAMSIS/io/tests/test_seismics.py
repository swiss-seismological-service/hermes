# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Testing facilities for seismic data import.
"""

import datetime
import os
import unittest

from unittest import mock

from ramsis.datamodel.status import Status  # noqa
from ramsis.datamodel.seismicity import SeismicityModel  # noqa
from ramsis.datamodel.forecast import Forecast  # noqa
from ramsis.datamodel.seismics import SeismicCatalog, SeismicEvent  # noqa
from ramsis.datamodel.well import InjectionWell  # noqa
from ramsis.datamodel.hydraulics import Hydraulics, InjectionPlan  # noqa
from ramsis.datamodel.settings import ProjectSettings  # noqa
from ramsis.datamodel.project import Project  # noqa

from RAMSIS.io.seismics import QuakeMLDeserializer
from RAMSIS.io.utils import (FileLikeResourceLoader, HTTPGETResourceLoader,
                             pymap3d_transform)


class QuakeMLDeserializerTestCase(unittest.TestCase):
    """
    Test for :py:class:`RAMSIS.io.seismics.QuakeMLDeserializer` class.
    """
    PATH_RESOURCES = 'resources'

    def test_with_filelike_loader(self):
        proj = '+x_0=0 +y_0=0 +z_0=0'
        with open(os.path.join(self.PATH_RESOURCES, 'cat.qml'), 'rb') as ifs:
            loader = FileLikeResourceLoader(ifs)

            deserializer = QuakeMLDeserializer(
                loader, proj=proj,
                transform_callback=pymap3d_transform)

            cat = deserializer.load()

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
    def test_with_http_get_loader(self, mock_req):

        def create_mock_resp():
            m = mock.MagicMock()
            p = mock.PropertyMock(return_value=200)
            type(m).status_code = p

            with open(
                    os.path.join(self.PATH_RESOURCES, 'cat.qml'), 'rb') as ifs:
                p = mock.PropertyMock(return_value=ifs.read())
                type(m).content = p

            return m

        mock_req.return_value = create_mock_resp()

        url = "http://foo.bar.com/fdsnws/event/1/query"
        req_params = {
            'starttime': '2019-01-01T00:00:00',
            'endtime': '2020-01-01T00:00:00',
            'format': 'xml',
            'magnitudetype': 'ML,Mc,MS,Mw', }
        loader = HTTPGETResourceLoader(url, req_params)

        proj = '+x_0=0 +y_0=0 +z_0=0'
        deserializer = QuakeMLDeserializer(
            loader, proj=proj,
            transform_callback=pymap3d_transform)

        cat = deserializer.load()

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


def suite():
    return unittest.makeSuite(QuakeMLDeserializerTestCase, 'test')


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
