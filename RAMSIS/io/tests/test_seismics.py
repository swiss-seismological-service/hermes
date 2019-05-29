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

        with open(os.path.join(self.PATH_RESOURCES, 'cat.qml'), 'rb') as ifs:
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

        with open(os.path.join(self.PATH_RESOURCES, 'cat.qml'), 'rb') as ifs:
            cat = deserializer.loads(ifs.read())

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


class QuakeMLCatalogSerializerTestCase(unittest.TestCase):
    """
    Test for :py:class:`RAMSIS.io.seismics.QuakeMLCatalogSerializer` class.
    """
    def test_dump_quakeml(self):

        event_first = b'<event publicID="smi:ch.ethz.sed/sc3a/2017epaqsp"><description><text>Linthal GL</text><type>region name</type></description><creationInfo><agencyID>SED</agencyID><author>scevent@sc3a</author><creationTime>2017-03-06T20:12:18.142256Z</creationTime></creationInfo><magnitude publicID="smi:ch.ethz.sed/sc3a/Magnitude/20180122172910.355937.96683"><stationCount>131</stationCount><creationInfo><agencyID>SED</agencyID><author>tdiehl@sc3ag</author><creationTime>2018-01-22T17:36:53.57853Z</creationTime></creationInfo><mag><value>4.628068684</value><uncertainty>0.3037482054</uncertainty></mag><type>MLh</type><methodID>smi:scs/0.7/median</methodID><evaluationStatus>confirmed</evaluationStatus></magnitude><origin publicID="smi:ch.ethz.sed/sc3a/origin/NLL.20180122172800.718443.96132"><time><value>2017-03-06T20:12:07.401209Z</value></time><longitude><value>8.925293642</value><uncertainty>0.1346011407</uncertainty></longitude><latitude><value>46.90669014</value><uncertainty>0.1545074617</uncertainty></latitude><quality><associatedPhaseCount>346</associatedPhaseCount><usedPhaseCount>219</usedPhaseCount><usedStationCount>168</usedStationCount><standardError>0.226300447</standardError><azimuthalGap>15.85593789</azimuthalGap><secondaryAzimuthalGap>23.65837089</secondaryAzimuthalGap><maximumDistance>1.089511519</maximumDistance><minimumDistance>0.05433250566</minimumDistance><medianDistance>0.8824018453</medianDistance><groundTruthLevel>-</groundTruthLevel></quality><evaluationMode>manual</evaluationMode><creationInfo><agencyID>SED</agencyID><author>tdiehl@sc3ag</author><creationTime>2018-01-22T17:29:02.102335Z</creationTime></creationInfo><depth><value>4223.144531</value><uncertainty>552.7772575</uncertainty></depth><originUncertainty><horizontalUncertainty>0.2356348945</horizontalUncertainty><minHorizontalUncertainty>0.2026160135</minHorizontalUncertainty><maxHorizontalUncertainty>0.2356348945</maxHorizontalUncertainty><azimuthMaxHorizontalUncertainty>168.0839685</azimuthMaxHorizontalUncertainty><confidenceEllipsoid><semiMajorAxisLength>1049.481209</semiMajorAxisLength><semiMinorAxisLength>243.4284848</semiMinorAxisLength><semiIntermediateAxisLength>257.2797378</semiIntermediateAxisLength><majorAxisPlunge>8.512110583</majorAxisPlunge><majorAxisAzimuth>-69.33752484</majorAxisAzimuth><majorAxisRotation>96.66478593</majorAxisRotation></confidenceEllipsoid></originUncertainty><methodID>smi:scs/0.7/NonLinLoc(L2)</methodID><earthModelID>smi:scs/0.7/swiss_3D_(Husen_2003)</earthModelID><evaluationStatus>confirmed</evaluationStatus></origin><preferredOriginID>smi:ch.ethz.sed/sc3a/origin/NLL.20180122172800.718443.96132</preferredOriginID><preferredMagnitudeID>smi:ch.ethz.sed/sc3a/Magnitude/20180122172910.355937.96683</preferredMagnitudeID><preferredFocalMechanismID>smi:ch.ethz.sed/sc3a/FocalMechanism/20171031112638.598333.34232</preferredFocalMechanismID><type>earthquake</type></event>' # noqa
        event_second = b'<event publicID="smi:ch.ethz.sed/KP201201242354.MANUPDEPICK/20121012194221/event/1"><description><text>Northern Italy</text><type>region name</type></description><typeCertainty>known</typeCertainty><creationInfo><agencyID>SED_KP</agencyID><agencyURI>smi:ch.ethz.sed/about-us</agencyURI><creationTime>2012-10-12T19:42:21.0000Z</creationTime></creationInfo><magnitude publicID="smi:ch.ethz.sed/KP201201242354.MANUPDEPICK/20121012194221/magnitude/1"><stationCount>27</stationCount><creationInfo><agencyID>SED_KP</agencyID><agencyURI>smi:ch.ethz.sed/about-us</agencyURI><author>ndeich</author><creationTime>2012-10-12T19:42:21.0000Z</creationTime></creationInfo><mag><value>4.4</value><uncertainty>0.4</uncertainty></mag><type>Ml</type><originID>smi:ch.ethz.sed/KP201201242354.MANUPDEPICK/20121012194221/origin/1</originID><methodID>smi:ch.ethz.sed/magnitudemethod/median</methodID></magnitude><origin publicID="smi:ch.ethz.sed/KP201201242354.MANUPDEPICK/20121012194221/origin/1"><time><value>2012-01-24T23:54:45.5Z</value></time><longitude><value>10.887</value></longitude><latitude><value>45.516</value></latitude><depthType>from location</depthType><quality><associatedPhaseCount>27</associatedPhaseCount><usedPhaseCount>27</usedPhaseCount><standardError>0.6</standardError><azimuthalGap>173</azimuthalGap><minimumDistance>0.2737492676</minimumDistance></quality><type>hypocenter</type><evaluationMode>manual</evaluationMode><creationInfo><agencyID>SED_KP</agencyID><agencyURI>smi:ch.ethz.sed/about-us</agencyURI><author>ndeich</author><creationTime>2012-10-12T19:42:21.0000Z</creationTime></creationInfo><depth><value>2000</value><uncertainty>1280</uncertainty></depth><originUncertainty><minHorizontalUncertainty>767</minHorizontalUncertainty><maxHorizontalUncertainty>982</maxHorizontalUncertainty><azimuthMaxHorizontalUncertainty>0</azimuthMaxHorizontalUncertainty></originUncertainty><methodID>smi:ch.ethz.sed/NonLinLoc_Ver._4.31.1_13Aug2007_c_Anthony_Lomax_-_anthony.at.alomax.net</methodID></origin><preferredOriginID>smi:ch.ethz.sed/KP201201242354.MANUPDEPICK/20121012194221/origin/1</preferredOriginID><preferredMagnitudeID>smi:ch.ethz.sed/KP201201242354.MANUPDEPICK/20121012194221/magnitude/1</preferredMagnitudeID><preferredFocalMechanismID>smi:ch.ethz.sed/sc3a/FocalMechanism/20150714123259.93049.37333</preferredFocalMechanismID><type>earthquake</type></event>' # noqa

        event_third = b'<event publicID="smi:ch.ethz.sed/event/ecos09/GROUP_PEGASOS/51764.00000"><typeCertainty>known</typeCertainty><creationInfo><agencyID>SED_ECOS-09</agencyID><agencyURI>smi:ch.ethz.sed/about-ecos</agencyURI></creationInfo><magnitude publicID="smi:ch.ethz.sed/magnitude/ecos09/Mw/627800"><creationInfo><agencyID>SED_ECOS09</agencyID><agencyURI>smi:ch.ethz.sed/about-ecos</agencyURI></creationInfo><mag><value>4.4</value><uncertainty>0.1</uncertainty><confidenceLevel>0.63</confidenceLevel></mag><type>Mw</type><originID>smi:ch.ethz.sed/origin/ecos09/DATANR/30331298.00000</originID><methodID>smi:ch.ethz.sed/magnitude/method/instr._SED_(Clinton_&gt;_60%VR)</methodID></magnitude><origin publicID="smi:ch.ethz.sed/origin/ecos09/DATANR/30331298.00000"><time><value>2005-09-08T11:27:17.0000Z</value></time><longitude><value>6.889</value><uncertainty>5</uncertainty></longitude><latitude><value>46.037</value><uncertainty>5</uncertainty></latitude><evaluationMode>manual</evaluationMode><creationInfo><agencyID>SED (ECOS-09)</agencyID></creationInfo><depth><value>4000</value><uncertainty>1000</uncertainty></depth><originUncertainty><horizontalUncertainty>5</horizontalUncertainty><minHorizontalUncertainty>5</minHorizontalUncertainty><maxHorizontalUncertainty>5</maxHorizontalUncertainty><azimuthMaxHorizontalUncertainty>0</azimuthMaxHorizontalUncertainty></originUncertainty><evaluationStatus>confirmed</evaluationStatus></origin><preferredOriginID>smi:ch.ethz.sed/origin/ecos09/DATANR/30331298.00000</preferredOriginID><preferredMagnitudeID>smi:ch.ethz.sed/magnitude/ecos09/Mw/627800</preferredMagnitudeID><type>earthquake</type></event>' # noqa

        reference_result = b'<?xml version="1.0" encoding="UTF-8"?><q:quakeml xmlns="http://quakeml.org/xmlns/bed/1.2" xmlns:q="http://quakeml.org/xmlns/quakeml/1.2"><eventParameters publicID="smi:scs/0.7/EventParameters"><event publicID="smi:ch.ethz.sed/sc3a/2017epaqsp"><description><text>Linthal GL</text><type>region name</type></description><creationInfo><agencyID>SED</agencyID><author>scevent@sc3a</author><creationTime>2017-03-06T20:12:18.142256Z</creationTime></creationInfo><magnitude publicID="smi:ch.ethz.sed/sc3a/Magnitude/20180122172910.355937.96683"><stationCount>131</stationCount><creationInfo><agencyID>SED</agencyID><author>tdiehl@sc3ag</author><creationTime>2018-01-22T17:36:53.57853Z</creationTime></creationInfo><mag><value>4.628068684</value><uncertainty>0.3037482054</uncertainty></mag><type>MLh</type><methodID>smi:scs/0.7/median</methodID><evaluationStatus>confirmed</evaluationStatus></magnitude><origin publicID="smi:ch.ethz.sed/sc3a/origin/NLL.20180122172800.718443.96132"><time><value>2017-03-06T20:12:07.401209Z</value></time><longitude><value>8.925293642</value><uncertainty>0.1346011407</uncertainty></longitude><latitude><value>46.90669014</value><uncertainty>0.1545074617</uncertainty></latitude><quality><associatedPhaseCount>346</associatedPhaseCount><usedPhaseCount>219</usedPhaseCount><usedStationCount>168</usedStationCount><standardError>0.226300447</standardError><azimuthalGap>15.85593789</azimuthalGap><secondaryAzimuthalGap>23.65837089</secondaryAzimuthalGap><maximumDistance>1.089511519</maximumDistance><minimumDistance>0.05433250566</minimumDistance><medianDistance>0.8824018453</medianDistance><groundTruthLevel>-</groundTruthLevel></quality><evaluationMode>manual</evaluationMode><creationInfo><agencyID>SED</agencyID><author>tdiehl@sc3ag</author><creationTime>2018-01-22T17:29:02.102335Z</creationTime></creationInfo><depth><value>4223.144531</value><uncertainty>552.7772575</uncertainty></depth><originUncertainty><horizontalUncertainty>0.2356348945</horizontalUncertainty><minHorizontalUncertainty>0.2026160135</minHorizontalUncertainty><maxHorizontalUncertainty>0.2356348945</maxHorizontalUncertainty><azimuthMaxHorizontalUncertainty>168.0839685</azimuthMaxHorizontalUncertainty><confidenceEllipsoid><semiMajorAxisLength>1049.481209</semiMajorAxisLength><semiMinorAxisLength>243.4284848</semiMinorAxisLength><semiIntermediateAxisLength>257.2797378</semiIntermediateAxisLength><majorAxisPlunge>8.512110583</majorAxisPlunge><majorAxisAzimuth>-69.33752484</majorAxisAzimuth><majorAxisRotation>96.66478593</majorAxisRotation></confidenceEllipsoid></originUncertainty><methodID>smi:scs/0.7/NonLinLoc(L2)</methodID><earthModelID>smi:scs/0.7/swiss_3D_(Husen_2003)</earthModelID><evaluationStatus>confirmed</evaluationStatus></origin><preferredOriginID>smi:ch.ethz.sed/sc3a/origin/NLL.20180122172800.718443.96132</preferredOriginID><preferredMagnitudeID>smi:ch.ethz.sed/sc3a/Magnitude/20180122172910.355937.96683</preferredMagnitudeID><preferredFocalMechanismID>smi:ch.ethz.sed/sc3a/FocalMechanism/20171031112638.598333.34232</preferredFocalMechanismID><type>earthquake</type></event><event publicID="smi:ch.ethz.sed/KP201201242354.MANUPDEPICK/20121012194221/event/1"><description><text>Northern Italy</text><type>region name</type></description><typeCertainty>known</typeCertainty><creationInfo><agencyID>SED_KP</agencyID><agencyURI>smi:ch.ethz.sed/about-us</agencyURI><creationTime>2012-10-12T19:42:21.0000Z</creationTime></creationInfo><magnitude publicID="smi:ch.ethz.sed/KP201201242354.MANUPDEPICK/20121012194221/magnitude/1"><stationCount>27</stationCount><creationInfo><agencyID>SED_KP</agencyID><agencyURI>smi:ch.ethz.sed/about-us</agencyURI><author>ndeich</author><creationTime>2012-10-12T19:42:21.0000Z</creationTime></creationInfo><mag><value>4.4</value><uncertainty>0.4</uncertainty></mag><type>Ml</type><originID>smi:ch.ethz.sed/KP201201242354.MANUPDEPICK/20121012194221/origin/1</originID><methodID>smi:ch.ethz.sed/magnitudemethod/median</methodID></magnitude><origin publicID="smi:ch.ethz.sed/KP201201242354.MANUPDEPICK/20121012194221/origin/1"><time><value>2012-01-24T23:54:45.5Z</value></time><longitude><value>10.887</value></longitude><latitude><value>45.516</value></latitude><depthType>from location</depthType><quality><associatedPhaseCount>27</associatedPhaseCount><usedPhaseCount>27</usedPhaseCount><standardError>0.6</standardError><azimuthalGap>173</azimuthalGap><minimumDistance>0.2737492676</minimumDistance></quality><type>hypocenter</type><evaluationMode>manual</evaluationMode><creationInfo><agencyID>SED_KP</agencyID><agencyURI>smi:ch.ethz.sed/about-us</agencyURI><author>ndeich</author><creationTime>2012-10-12T19:42:21.0000Z</creationTime></creationInfo><depth><value>2000</value><uncertainty>1280</uncertainty></depth><originUncertainty><minHorizontalUncertainty>767</minHorizontalUncertainty><maxHorizontalUncertainty>982</maxHorizontalUncertainty><azimuthMaxHorizontalUncertainty>0</azimuthMaxHorizontalUncertainty></originUncertainty><methodID>smi:ch.ethz.sed/NonLinLoc_Ver._4.31.1_13Aug2007_c_Anthony_Lomax_-_anthony.at.alomax.net</methodID></origin><preferredOriginID>smi:ch.ethz.sed/KP201201242354.MANUPDEPICK/20121012194221/origin/1</preferredOriginID><preferredMagnitudeID>smi:ch.ethz.sed/KP201201242354.MANUPDEPICK/20121012194221/magnitude/1</preferredMagnitudeID><preferredFocalMechanismID>smi:ch.ethz.sed/sc3a/FocalMechanism/20150714123259.93049.37333</preferredFocalMechanismID><type>earthquake</type></event><event publicID="smi:ch.ethz.sed/event/ecos09/GROUP_PEGASOS/51764.00000"><typeCertainty>known</typeCertainty><creationInfo><agencyID>SED_ECOS-09</agencyID><agencyURI>smi:ch.ethz.sed/about-ecos</agencyURI></creationInfo><magnitude publicID="smi:ch.ethz.sed/magnitude/ecos09/Mw/627800"><creationInfo><agencyID>SED_ECOS09</agencyID><agencyURI>smi:ch.ethz.sed/about-ecos</agencyURI></creationInfo><mag><value>4.4</value><uncertainty>0.1</uncertainty><confidenceLevel>0.63</confidenceLevel></mag><type>Mw</type><originID>smi:ch.ethz.sed/origin/ecos09/DATANR/30331298.00000</originID><methodID>smi:ch.ethz.sed/magnitude/method/instr._SED_(Clinton_&gt;_60%VR)</methodID></magnitude><origin publicID="smi:ch.ethz.sed/origin/ecos09/DATANR/30331298.00000"><time><value>2005-09-08T11:27:17.0000Z</value></time><longitude><value>6.889</value><uncertainty>5</uncertainty></longitude><latitude><value>46.037</value><uncertainty>5</uncertainty></latitude><evaluationMode>manual</evaluationMode><creationInfo><agencyID>SED (ECOS-09)</agencyID></creationInfo><depth><value>4000</value><uncertainty>1000</uncertainty></depth><originUncertainty><horizontalUncertainty>5</horizontalUncertainty><minHorizontalUncertainty>5</minHorizontalUncertainty><maxHorizontalUncertainty>5</maxHorizontalUncertainty><azimuthMaxHorizontalUncertainty>0</azimuthMaxHorizontalUncertainty></originUncertainty><evaluationStatus>confirmed</evaluationStatus></origin><preferredOriginID>smi:ch.ethz.sed/origin/ecos09/DATANR/30331298.00000</preferredOriginID><preferredMagnitudeID>smi:ch.ethz.sed/magnitude/ecos09/Mw/627800</preferredMagnitudeID><type>earthquake</type></event></eventParameters></q:quakeml>'  # noqa

        events = [SeismicEvent(quakeml=event_first),
                  SeismicEvent(quakeml=event_second),
                  SeismicEvent(quakeml=event_third)]

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
