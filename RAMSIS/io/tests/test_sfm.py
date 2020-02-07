# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Testing facilities for SFM-Worker IO.
"""

import base64
import datetime
import json
import os
import unittest
import uuid

import dateutil
import dateutil.parser

from ramsis.datamodel.status import Status  # noqa
from ramsis.datamodel.seismicity import SeismicityModel  # noqa
from ramsis.datamodel.forecast import Forecast  # noqa
from ramsis.datamodel.seismics import SeismicCatalog, SeismicEvent  # noqa
from ramsis.datamodel.seismicity import (ReservoirSeismicityPrediction,
                                         SeismicityPredictionBin)
from ramsis.datamodel.well import InjectionWell, WellSection  # noqa
from ramsis.datamodel.hydraulics import (Hydraulics, InjectionPlan,  # noqa
                                         HydraulicSample) # noqa
from ramsis.datamodel.settings import ProjectSettings  # noqa
from ramsis.datamodel.project import Project  # noqa

from RAMSIS.io.sfm import (SFMWorkerIMessageSerializer,
                           SFMWorkerOMessageDeserializer)


RAMSIS_PROJ = ("+proj=utm +zone=32N +ellps=WGS84 +datum=WGS84 "
               "+units=m +x_0=0.0 +y_0=0.0 +no_defs")
WGS84_PROJ = "epsg:4326"
REFERENCE_X = 681922.0
REFERENCE_Y = 1179229.0

LAT = 10.663204912654692
LON = 10.663205540045357


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
    maxDiff = None

    def test_dumps_imessage(self):
        reservoir = {
            "x": [-2000.0, 0.0, 2000.0],
            "y": [-2000.0, 0.0, 2000.0],
            "z": [-4000.0, -2000.0, 0.0]}
        reference_catalog = _read(os.path.join(self.PATH_RESOURCES,
                                               'cat-01.qml'))
        reference_catalog = base64.b64encode(
            reference_catalog).decode('utf-8')

        attributes = {
            'seismic_catalog': {
                'quakeml': reference_catalog},
            'well': {
                'altitude': {'value': 400.0},
                'publicid': ('smi:ch.ethz.sed/bh/'
                             '11111111-e4a0-4692-bf29-33b5591eb798'),
                'sections': [{
                    'toplongitude': {'value': LON},
                    'toplatitude': {'value': LAT},
                    'topdepth': {'value': 0.0},
                    'bottomlongitude': {'value': LON},
                    'bottomlatitude': {'value': LAT},
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
                            {'value': '2019-05-03T15:27:09.117623'}}]}]},
            'scenario': {
                'well': {
                    'altitude': {'value': 400.0},
                    'publicid': ('smi:ch.ethz.sed/bh/'
                                 '11111111-e4a0-4692-bf29-33b5591eb798'),
                    'sections': [{
                        'toplongitude': {'value': LON},
                        'toplatitude': {'value': LAT},
                        'topdepth': {'value': 0.0},
                        'bottomlongitude': {'value': LON},
                        'bottomlatitude': {'value': LAT},
                        'bottomdepth': {'value': 1000.0},
                        'holediameter': {'value': 0.3},
                        'topclosed': False,
                        'bottomclosed': False,
                        'publicid': ('smi:ch.ethz.sed/bh/section/'
                                 '11111111-8d89-4f13-95e7-526ade73cc8b'),
                        'hydraulics': [
                            {'datetime':
                                {'value': '2019-05-03T17:27:09.117623'}},
                            {'datetime':
                                {'value': '2019-05-03T19:27:09.117623'}}]}]}},
                'reservoir': {
                    'geom': reservoir},
                'spatialreference': RAMSIS_PROJ,
                'referencepoint': {'x': REFERENCE_X, 'y': REFERENCE_Y}}

        reference_result = {
            'data': {
                'type': 'runs',
                'attributes': attributes}}

        event_0 = _read(os.path.join(self.PATH_RESOURCES, 'e-00.qmlevent'))
        event_1 = _read(os.path.join(self.PATH_RESOURCES, 'e-01.qmlevent'))
        event_2 = _read(os.path.join(self.PATH_RESOURCES, 'e-02.qmlevent'))

        events = [SeismicEvent(quakeml=event_0),
                  SeismicEvent(quakeml=event_1),
                  SeismicEvent(quakeml=event_2)]

        catalog = SeismicCatalog(events=events)

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
            topx_value=0.0,
            topy_value=0.0,
            topz_value=400.0,
            bottomx_value=0.0,
            bottomy_value=0.0,
            bottomz_value=-600,
            holediameter_value=0.3,
            topclosed=False,
            bottomclosed=False,
            hydraulics=hyd)

        bh = InjectionWell(
            publicid='smi:ch.ethz.sed/bh/11111111-e4a0-4692-bf29-33b5591eb798',
            altitude_value=400.0,
            sections=[sec])
        plan = InjectionPlan(samples=[s2, s3])

        sec_scenario = WellSection(
            publicid=('smi:ch.ethz.sed/bh/section/'
                      '11111111-8d89-4f13-95e7-526ade73cc8b'),
            topx_value=0.0,
            topy_value=0.0,
            topz_value=400.0,
            bottomx_value=0,
            bottomy_value=0,
            bottomz_value=-600,
            holediameter_value=0.3,
            topclosed=False,
            bottomclosed=False,
            injectionplan=plan)
        bh_scenario = InjectionWell(
            publicid='smi:ch.ethz.sed/bh/11111111-e4a0-4692-bf29-33b5591eb798',
            altitude_value=400.0,
            sections=[sec_scenario])

        serializer = SFMWorkerIMessageSerializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_from_local_coords')

        payload = {
            'data': {
                'attributes': {
                    'seismic_catalog': {'quakeml': catalog},
                    'well': bh,
                    'scenario': {'well': bh_scenario},
                    'reservoir': {'geom': reservoir},
                    'spatialreference': RAMSIS_PROJ,
                    'referencepoint': {'x': REFERENCE_X, 'y': REFERENCE_Y},
                    'model_parameters': {}}}}

        actual_result = json.loads(serializer.dumps(payload))
        self.assertEqual(reference_result, actual_result)


class SFMWorkerOMessageDeserializerTestCase(unittest.TestCase):
    """
    Test for :py:class:`RAMSIS.io.sfm.SFMWorkerOMessageDeserializer` class.
    """

    PATH_RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'resources')

    def test_error_msg(self):
        json_omsg = _read(os.path.join(self.PATH_RESOURCES,
                                       'omsg-500.json'))

        reference_result = {
            'data': {
                'id': uuid.UUID('491a85d6-04b3-4528-8422-acb348f5955b'),
                'attributes': {
                    'status_code': 500,
                    'status': 'WorkerError',
                    'warning': 'Caught in default model exception handler.'}}}

        deserializer = SFMWorkerOMessageDeserializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_to_local_coords')

        self.assertEqual(deserializer.loads(json_omsg),
                         reference_result)

    def test_accepted_msg(self):
        json_omsg = _read(os.path.join(self.PATH_RESOURCES,
                                       'omsg-202.json'))

        reference_result = {
            'data': {
                'id': uuid.UUID('f51e0208-515d-4099-8d87-bdc0e54f09cb'),
                'attributes': {
                    'status_code': 202,
                    'status': 'TaskAccepted',
                    'warning': '', }}}

        deserializer = SFMWorkerOMessageDeserializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_to_local_coords')

        self.assertEqual(deserializer.loads(json_omsg),
                         reference_result)

    def test_ok_msg(self):
        json_omsg = _read(os.path.join(self.PATH_RESOURCES,
                                       'omsg-200.json'))

        s0 = SeismicityPredictionBin(
            starttime=dateutil.parser.parse(
                '2019-07-02T14:59:52.508142'),
            endtime=dateutil.parser.parse('2019-07-02T14:59:52.508142'),
            b_value=73,
            a_value=1.,
            mc_value=1.5,
            hydraulicvol_value=10000.)

        prediction = ReservoirSeismicityPrediction(
            x_min=-2000,
            x_max=0,
            y_min=-2000,
            y_max=0,
            z_min=-4000,
            z_max=-2000,
            samples=[s0, ])

        reference_result = {
            'data': {
                'id': uuid.UUID('491a85d6-04b3-4528-8422-acb348f5955b'),
                'attributes': {
                    'status_code': 200,
                    'status': 'TaskCompleted',
                    'warning': '',
                    'forecast': prediction}}}

        deserializer = SFMWorkerOMessageDeserializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_to_local_coords')

        self.assertEqual(deserializer.loads(json_omsg),
                         reference_result)

    def test_ok_dict(self):
        json_omsg = _read(os.path.join(self.PATH_RESOURCES,
                                       'omsg-200.json'))

        s0 = dict(
            starttime=dateutil.parser.parse(
                '2019-07-02T14:59:52.508142'),
            endtime=dateutil.parser.parse('2019-07-02T14:59:52.508143'),
            b_value=73.,
            a_value=1.,
            mc_value=1.5,
            numberevents_value=42.,
            hydraulicvol_value=10000.)

        prediction = dict(
            x_min=-2000,
            x_max=0,
            y_min=-2000,
            y_max=0,
            z_min=-4000,
            z_max=-2000,
            samples=[s0, ])

        reference_result = {
            'data': {
                'id': uuid.UUID('491a85d6-04b3-4528-8422-acb348f5955b'),
                'attributes': {
                    'status_code': 200,
                    'status': 'TaskCompleted',
                    'warning': '',
                    'forecast': prediction}}}

        deserializer = SFMWorkerOMessageDeserializer(
            ramsis_proj=RAMSIS_PROJ,
            external_proj=WGS84_PROJ,
            ref_easting=REFERENCE_X,
            ref_northing=REFERENCE_Y,
            transform_func_name='pyproj_transform_to_local_coords',
            context={'format': 'dict'})

        self.assertEqual(deserializer.loads(json_omsg),
                         reference_result)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(
        unittest.makeSuite(SFMWorkerIMessageSerializerTestCase, 'test'))
    suite.addTest(
        unittest.makeSuite(SFMWorkerOMessageDeserializerTestCase, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
