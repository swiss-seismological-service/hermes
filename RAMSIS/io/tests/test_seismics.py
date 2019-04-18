# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Testing facilities for seismic data import.
"""

import datetime
import os
import unittest

from ramsis.datamodel.status import Status  # noqa
from ramsis.datamodel.seismicity import SeismicityModel  # noqa
from ramsis.datamodel.forecast import Forecast  # noqa
from ramsis.datamodel.seismics import SeismicCatalog, SeismicEvent  # noqa
from ramsis.datamodel.well import InjectionWell  # noqa
from ramsis.datamodel.hydraulics import Hydraulics, InjectionPlan  # noqa
from ramsis.datamodel.settings import ProjectSettings  # noqa
from ramsis.datamodel.project import Project  # noqa

from RAMSIS.io.seismics import QuakeMLDeserializer
from RAMSIS.io.utils import FileLikeResourceLoader, pymap3d_transform


class QuakeMLDeserializerTestCase(unittest.TestCase):
    """
    Test for :py:class:`RAMSIS.io.seismics.QuakeMLDeserializer` class.
    """
    PATH_RESOURCES = 'resources'

    def test_with_filelike_loader(self):
        proj = '+x_0=0 +y_0=0 +z_0=0'
        with open(os.path.join(self.PATH_RESOURCES, 'cat.qml'), 'rb') as ifs:
            loader = FileLikeResourceLoader(ifs)

            deserializer = QuakeMLDeserializer(loader, proj=proj)

            @deserializer.transform_callback
            def crs_transform(x, y, z, proj):
                return pymap3d_transform(x, y, z, proj)

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
