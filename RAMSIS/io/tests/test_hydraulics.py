# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Testing facilities for borehole/hydraulics data import.
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

from RAMSIS.io.hydraulics import HYDWSBoreholeHydraulicsDeserializer
from RAMSIS.io.utils import (FileLikeResourceLoader, HTTPGETResourceLoader,
                             pymap3d_transform)


class HYDWSBoreholeHydraulicsDeserializerTestCase(unittest.TestCase):
    """
    Test for the
    :py:class:`RAMSIS.io.hydraulics.HYDWSBoreholeHydraulicsDeserializer` class.
    """
    PATH_RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'resources')

    def test_with_filelike_loader(self):
        proj = '+x_0=0 +y_0=0 +z_0=0'
        with open(os.path.join(self.PATH_RESOURCES, 'hyd.json'), 'rb') as ifs:
            loader = FileLikeResourceLoader(ifs)

            deserializer = HYDWSBoreholeHydraulicsDeserializer(
                loader, proj=proj,
                transform_callback=pymap3d_transform)

            bh = deserializer.load()

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
    def test_with_http_get_loader(self, mock_req):

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
        loader = HTTPGETResourceLoader(url, req_params)
        proj = '+x_0=0 +y_0=0 +z_0=0'

        deserializer = HYDWSBoreholeHydraulicsDeserializer(
            loader, proj=proj,
            transform_callback=pymap3d_transform)

        bh = deserializer.load()

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
