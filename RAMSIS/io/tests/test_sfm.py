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
from RAMSIS.io.utils import (pymap3d_transform_ned2geodetic,
                             pymap3d_transform_geodetic2ned)


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

        attributes = {
            'seismic_catalog': {
                'quakeml': reference_catalog},
            'well': {
                'sections': [{
                    'toplongitude': {'value': 8.525519556860086},
                    'toplatitude': {'value': 47.370296812745515},
                    'topdepth': {'value': 408.0391832907959},
                    'bottomlongitude': {'value': 8.525520385756767},
                    'bottomlatitude': {'value': 47.3702973775022},
                    'bottomdepth': {'value': -391.9608117940517},
                    'holediameter': {'value': 0.3},
                    'topclosed': False,
                    'bottomclosed': False,
                    'publicid': ('smi:ch.ethz.sed/bh/section/'
                                 '11111111-8d89-4f13-95e7-526ade73cc8b'),
                    'hydraulics': [
                        {'datetime':
                            {'value': '2019-05-03T13:27:09.117623'}},
                        {'datetime':
                            {'value': '2019-05-03T15:27:09.117623'}}]}],
                    'publicid': ('smi:ch.ethz.sed/bh/'
                                 '11111111-e4a0-4692-bf29-33b5591eb798')},
            'scenario': {
                'well': {
                    'sections': [{
                        'toplongitude': {'value': 8.525519556860086},
                        'toplatitude': {'value': 47.370296812745515},
                        'topdepth': {'value': 408.0391832907959},
                        'bottomlongitude': {'value': 8.525520385756767},
                        'bottomlatitude': {'value': 47.3702973775022},
                        'bottomdepth': {'value': -391.9608117940517},
                        'holediameter': {'value': 0.3},
                        'topclosed': False,
                        'bottomclosed': False,
                        'publicid': ('smi:ch.ethz.sed/bh/section/'
                                     '11111111-8d89-4f13-95e7-526ade73cc8b'),
                        'hydraulics': [
                            {'datetime':
                                {'value': '2019-05-03T17:27:09.117623'}},
                            {'datetime':
                                {'value': ('2019-05-03T'
                                           '19:27:09.117623')}}]}],
                        'publicid': ('smi:ch.ethz.sed/bh/'
                                     '11111111-e4a0-4692-bf29-33b5591eb798')}},
                'reservoir': {'geom':
                              ('POLYHEDRALSURFACE Z ('
                               '((8.5189 47.3658 408.000000000195,'
                               '8.5189 47.3747940041495 408.078487513805,'
                               '8.53214023892212 47.3747932395126 '
                               '408.156733124709,'
                               '8.5321379883561 47.3657992356023 '
                               '408.078245651359,'
                               '8.5189 47.3658 408.000000000195)),'
                               '((8.5189 47.3658 408.000000000195,'
                               '8.5189 47.3747940041495 408.078487513805,'
                               '8.5189 47.3747954162037 -591.921500163549,'
                               '8.5189 47.3658 -591.999999998976,'
                               '8.5189 47.3658 408.000000000195)),'
                               '((8.5189 47.3658 408.000000000195,'
                               '8.5321379883561 47.3657992356023 '
                               '408.078245651359,'
                               '8.53214006031033 47.3657992353626 '
                               '-591.921742101363,'
                               '8.5189 47.3658 -591.999999998976,'
                               '8.5189 47.3658 408.000000000195)),'
                               '((8.53214231158096 47.374794651327 '
                               '-591.843242307722,'
                               '8.53214006031033 47.3657992353626 '
                               '-591.921742101363,'
                               '8.5189 47.3658 -591.999999998976,'
                               '8.5189 47.3747954162037 -591.921500163549,'
                               '8.53214231158096 47.374794651327 '
                               '-591.843242307722)),'
                               '((8.53214231158096 47.374794651327 '
                               '-591.843242307722,'
                               '8.53214006031033 47.3657992353626 '
                               '-591.921742101363,'
                               '8.5321379883561 47.3657992356023 '
                               '408.078245651359,'
                               '8.53214023892212 47.3747932395126 '
                               '408.156733124709,'
                               '8.53214231158096 47.374794651327 '
                               '-591.843242307722)),'
                               '((8.53214231158096 47.374794651327 '
                               '-591.843242307722,'
                               '8.53214023892212 47.3747932395126 '
                               '408.156733124709,'
                               '8.5189 47.3747940041495 408.078487513805,'
                               '8.5189 47.3747954162037 -591.921500163549,'
                               '8.53214231158096 47.374794651327 '
                               '-591.843242307722)))')}}

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

        reservoir = ('POLYHEDRALSURFACE Z '
                     '(((0 0 0, 0 1000 0, 1000 1000 0, 1000 0 0, '
                     '0 0 0)),'
                     '((0 0 0, 0 1000 0, 0 1000 1000, 0 0 1000, '
                     '0 0 0)),'
                     '((0 0 0, 1000 0 0, 1000 0 1000, 0 0 1000, '
                     '0 0 0)),'
                     '((1000 1000 1000, 1000 0 1000, 0 0 1000, '
                     '0 1000 1000, 1000 1000 1000)),'
                     '((1000 1000 1000, 1000 0 1000, 1000 0 0, '
                     '1000 1000 0, 1000 1000 1000)),'
                     '((1000 1000 1000, 1000 1000 0, 0 1000 0, '
                     '0 1000 1000, 1000 1000 1000)))')

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
            toplongitude_value=500.0,
            toplatitude_value=500.0,
            topdepth_value=0,
            bottomlongitude_value=500,
            bottomlatitude_value=500,
            bottomdepth_value=800,
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
            toplongitude_value=500.0,
            toplatitude_value=500.0,
            topdepth_value=0,
            bottomlongitude_value=500,
            bottomlatitude_value=500,
            bottomdepth_value=800,
            holediameter_value=0.3,
            topclosed=False,
            bottomclosed=False,
            injectionplan=plan)

        bh_scenario = InjectionWell(
            publicid='smi:ch.ethz.sed/bh/11111111-e4a0-4692-bf29-33b5591eb798',
            sections=[sec_scenario])

        proj = '+x_0=8.5189 +y_0=47.3658 +z_0=408'
        serializer = SFMWorkerIMessageSerializer(
            proj=proj, transform_callback=pymap3d_transform_ned2geodetic)

        payload = {
            'data': {
                'attributes': {
                    'seismic_catalog': {'quakeml': catalog},
                    'well': bh,
                    'scenario': {'well': bh_scenario},
                    'reservoir': {'geom': reservoir},
                    'model_parameters': {}}}}

        self.assertEqual(reference_result,
                         json.loads(serializer.dumps(payload)))

    def test_no_proj(self):

        reference_catalog = _read(os.path.join(self.PATH_RESOURCES,
                                               'cat-01.qml'))
        reference_catalog = base64.b64encode(
            reference_catalog).decode('utf-8')

        attributes = {
            'seismic_catalog': {
                'quakeml': reference_catalog},
            'well': {
                'sections': [{
                    'toplongitude': {'value': 10.663207130000002},
                    'toplatitude': {'value': 10.66320713},
                    'topdepth': {'value': 0.0},
                    'bottomlatitude': {'value': 10.66320713},
                    'bottomlongitude': {'value': 10.66320713},
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
                            {'value': '2019-05-03T15:27:09.117623'}}]}],
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
                                {'value': ('2019-05-03T19:27:09.117623')}}]}],
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
            toplongitude_value=10.663207130000002,
            toplatitude_value=10.66320713,
            topdepth_value=0.0,
            bottomlongitude_value=10.66320713,
            bottomlatitude_value=10.66320713,
            bottomdepth_value=1000.0,
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
            toplongitude_value=10.663207130000002,
            toplatitude_value=10.66320713,
            topdepth_value=0.0,
            bottomlongitude_value=10.66320713,
            bottomlatitude_value=10.66320713,
            bottomdepth_value=1000.0,
            holediameter_value=0.3,
            topclosed=False,
            bottomclosed=False,
            injectionplan=plan)

        bh_scenario = InjectionWell(
            publicid='smi:ch.ethz.sed/bh/11111111-e4a0-4692-bf29-33b5591eb798',
            sections=[sec_scenario])

        serializer = SFMWorkerIMessageSerializer(proj=None)

        payload = {
            'data': {
                'attributes': {
                    'seismic_catalog': {'quakeml': catalog},
                    'well': bh,
                    'scenario': {'well': bh_scenario},
                    'reservoir': {'geom': reservoir},
                    'model_parameters': {}}}}

        self.assertEqual(reference_result,
                         json.loads(serializer.dumps(payload)))


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

        proj = '+x_0=8.5189 +y_0=47.3658 +z_0=408'
        deserializer = SFMWorkerOMessageDeserializer(
            proj=proj, transform_callback=pymap3d_transform_geodetic2ned)

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

        deserializer = SFMWorkerOMessageDeserializer(proj=None)

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
            geom=('POLYHEDRALSURFACE Z '
                  '(((-944829.45117427 -4619265.09168063 2094632.70852796,'
                  '-944257.736152511 -4466699.60773925 1934552.84972869,'
                  '-723677.819288185 -4488118.51527331 1914833.54607117,'
                  '-724115.980887884 -4640696.9676138 2074901.46552201,'
                  '-944829.45117427 -4619265.09168063 2094632.70852796)),'
                  '((-944829.45117427 -4619265.09168063 2094632.70852796,'
                  '-944257.736152511 -4466699.60773925 1934552.84972869,'
                  '-944258.032243325 -4466701.01472902 1934551.45950928,'
                  '-944829.747445564 -4619266.54683276 2094631.36884307,'
                  '-944829.45117427 -4619265.09168063 2094632.70852796)),'
                  '((-944829.45117427 -4619265.09168063 2094632.70852796,'
                  '-724115.980887884 -4640696.9676138 2074901.46552201,'
                  '-724116.207949793 -4640698.42948635 2074900.11964997,'
                  '-944829.747445564 -4619266.54683276 2094631.36884307,'
                  '-944829.45117427 -4619265.09168063 2094632.70852796)),'
                  '((-723678.046211774 -4488119.9289794 1914832.14966838,'
                  '-724116.207949793 -4640698.42948635 2074900.11964997,'
                  '-944829.747445564 -4619266.54683276 2094631.36884307,'
                  '-944258.032243325 -4466701.01472902 1934551.45950928,'
                  '-723678.046211774 -4488119.9289794 1914832.14966838)),'
                  '((-723678.046211774 -4488119.9289794 1914832.14966838,'
                  '-724116.207949793 -4640698.42948635 2074900.11964997,'
                  '-724115.980887884 -4640696.9676138 2074901.46552201,'
                  '-723677.819288185 -4488118.51527331 1914833.54607117,'
                  '-723678.046211774 -4488119.9289794 1914832.14966838)),'
                  '((-723678.046211774 -4488119.9289794 1914832.14966838,'
                  '-723677.819288185 -4488118.51527331 1914833.54607117,'
                  '-944257.736152511 -4466699.60773925 1934552.84972869,'
                  '-944258.032243325 -4466701.01472902 1934551.45950928,'
                  '-723678.046211774 -4488119.9289794 1914832.14966838)))'),
            samples=[s0, ])

        reference_result = {
            'data': {
                'id': uuid.UUID('491a85d6-04b3-4528-8422-acb348f5955b'),
                'attributes': {
                    'status_code': 200,
                    'status': 'TaskCompleted',
                    'warning': '',
                    'forecast': prediction}}}

        proj = '+x_0=8.5189 +y_0=47.3658 +z_0=408'
        deserializer = SFMWorkerOMessageDeserializer(
            proj=proj, transform_callback=pymap3d_transform_geodetic2ned)

        self.assertEqual(deserializer.loads(json_omsg),
                         reference_result)

    def test_no_proj(self):
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
            geom=('POLYHEDRALSURFACE Z '
                  '(((0 0 0,0 2 0,2 2 0,2 0 0,0 0 0)),'
                  '((0 0 0,0 2 0,0 2 2,0 0 2,0 0 0)),'
                  '((0 0 0,2 0 0,2 0 2,0 0 2,0 0 0)),'
                  '((2 2 2,2 0 2,0 0 2,0 2 2,2 2 2)),'
                  '((2 2 2,2 0 2,2 0 0,2 2 0,2 2 2)),'
                  '((2 2 2,2 2 0,0 2 0,0 2 2,2 2 2)))'),
            samples=[s0, ])

        reference_result = {
            'data': {
                'id': uuid.UUID('491a85d6-04b3-4528-8422-acb348f5955b'),
                'attributes': {
                    'status_code': 200,
                    'status': 'TaskCompleted',
                    'warning': '',
                    'forecast': prediction}}}

        deserializer = SFMWorkerOMessageDeserializer(proj=None)

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
            hydraulicvol=10000.)

        prediction = dict(
            geom=('POLYHEDRALSURFACE Z '
                  '(((0 0 0,0 2 0,2 2 0,2 0 0,0 0 0)),'
                  '((0 0 0,0 2 0,0 2 2,0 0 2,0 0 0)),'
                  '((0 0 0,2 0 0,2 0 2,0 0 2,0 0 0)),'
                  '((2 2 2,2 0 2,0 0 2,0 2 2,2 2 2)),'
                  '((2 2 2,2 0 2,2 0 0,2 2 0,2 2 2)),'
                  '((2 2 2,2 2 0,0 2 0,0 2 2,2 2 2)))'),
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
            proj=None, context={'format': 'dict'})

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
