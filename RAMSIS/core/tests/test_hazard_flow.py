"""
test_hazard_flow.py

Integration test for core workflow. This test requires set-up of
a docker container to run the code in (not recommended to use the RAMSIS
container, although this is possible.) The docker container needs to have
postgres and postgis enabled, recomend using kartoza/postgis
https://hub.docker.com/r/kartoza/postgis/
(   Shouldnt need to pull image as image should already exist
    but to get latest image...
    $ docker pull kartoza/postgis)
$ docker run --rm   --name pg-test -d -p 5435:5432 kartoza/postgis

Where the name does not matter, the port 5435 is the port you
can access the postgresql db on your machine. This has been set to
the default port for the test, but can be changed.

IMPORTANT
Due to the multithreading used by the core core, these tests must
be run with unittest in the following way:
    $ python core/tests/test_forecast_flow.py
    or
    $ unittest core/tests/test_forecast_flow.py
but not with pytest currently. This is due to an open issue regarding
logging https://github.com/pytest-dev/pytest/issues/5502
where the buffer for pytest is closed before the core loggers and this
leads to errors.
"""
from copy import copy
from io import BufferedReader
import zipfile
import unittest
from unittest import mock
import time
import os
import psycopg2
import argparse
import json

from datetime import datetime, timedelta

from ramsis.datamodel.forecast import (  # noqa
    Forecast, ForecastScenario, ForecastStage, SeismicityForecastStage,
    SeismicitySkillStage, HazardStage, RiskStage, EStage)
from ramsis.datamodel.hydraulics import (  # noqa
    Hydraulics, InjectionPlan, HydraulicSample)
from ramsis.datamodel.model import Model, ModelRun, EModel  # noqa
from ramsis.datamodel.project import Project  # noqa
from ramsis.datamodel.seismicity import (  # noqa
    SeismicityModel, SeismicityModelRun, ReservoirSeismicityPrediction,
    SeismicityPredictionBin)
from ramsis.datamodel.seismics import SeismicCatalog, SeismicEvent  # noqa
from ramsis.datamodel.settings import ProjectSettings  # noqa
from ramsis.datamodel.status import Status, EStatus  # noqa
from ramsis.datamodel.well import InjectionWell, WellSection  # noqa
from ramsis.datamodel.hazard import HazardModel, HazardModelRun

from RAMSIS.core.builder import (
    default_project, default_forecast, default_scenario)
from RAMSIS.core.controller import Controller, LaunchMode
from RAMSIS.core.store import Store
from RAMSIS.io.hydraulics import HYDWSBoreholeHydraulicsDeserializer
from RAMSIS.io.seismics import QuakeMLCatalogDeserializer

PATH_SEISMICS = 'catalog_data/seismics.qml'
# Only ~this many files can be imported and merged before
# memory error occurs.
PATHS_HYDRAULICS = [
    'hyd_data/basel-2006-01.json']

dirpath = os.path.dirname(os.path.abspath(__file__))

LOGIC_TREE_TEMPLATE = os.path.join(dirpath,
                                   'hazard_templates',
                                   'logic_tree_template.xml')
GMPE_TEMPLATE = os.path.join(dirpath,
                             'hazard_templates',
                             'gmpe_file.xml')
JOB_CONFIG_TEMPLATE = os.path.join(dirpath,
                                   'hazard_templates',
                                   'job.ini')
SOURCE_MODEL_TEMPLATE = os.path.join(
    dirpath, 'hazard_templates', 'single_reservoir_seismicity_template.xml')

RAMSIS_PROJ = ("+proj=utm +zone=32N +ellps=WGS84 +datum=WGS84 +units=m "
               "+x_0=0.0 +y_0=0.0 +no_defs")
WGS84_PROJ = "epsg:4326"
REFERENCE_X = 681922
REFERENCE_Y = 1179229

PATH_SEISMICS = 'catalog_data/seismics.qml'
# Only ~this many files can be imported and merged before
# memory error occurs.
PATHS_HYDRAULICS = [
    'hyd_data/hyd-arnaud-alt.json']

PATH_INJECTION_PLAN = 'injection_data/injectionplan-mignan.json'

POST_RESPONSE1 = 'oq_responses/post_response1'
POST_RESPONSE2 = 'oq_responses/post_response2'
XML_RESULTS_BINARY1 = 'oq_responses/xml_result_curves_zip1'
XML_RESULTS_BINARY2 = 'oq_responses/xml_result_curves_zip2'
XML_RESULTS_BINARY_MAPS1 = 'oq_responses/xml_result_maps_zip1'
XML_RESULTS_BINARY_MAPS2 = 'oq_responses/xml_result_maps_zip2'
RESPONSE_LIST_BINARY = 'oq_responses/response_result_list1'
RESPONSE_STATUS_BINARY = 'oq_responses/response_result_status1'


PROJECT_STARTTIME = datetime(2006, 12, 2)
PROJECT_ENDTIME = None

FORECAST_STARTTIME = PROJECT_STARTTIME
FORECAST_ENDTIME = datetime(2006, 12, 2, 0, 30)

# NOTE(sarsonl): Reservoir definition containing all seismic events.
RESERVOIR_INPUT = {"x": [-2000, 2000], "y": [-2000, 2000], "z": [-4000, 0]}
X_MIN = -2000
X_MAX = 2000
Y_MIN = -2000
Y_MAX = 2000
Z_MIN = -4000
Z_MAX = 0

GEOPOINTS = 'results_data/hazard_geopoints.txt'

JSON_GET_TEMPLATE = {
    "data": {
        "id": None,
        "attributes": {
            "status": "TaskCompleted",
            "status_code": 200,
            "forecast": {
                "x_min": X_MIN,
                "y_min": Y_MIN,
                "z_min": Z_MIN,
                "x_max": X_MAX,
                "y_max": Y_MAX,
                "z_max": Z_MAX,
                "samples": [
                    {
                        "starttime": "2015-05-07T00:00:00",
                        "endtime": "2015-05-07T04:00:00",
                        "numberevents": {
                            "value": 1.8
                        },
                        "hydraulicvol": {
                            "value": 129600.0
                        },
                        "b": {
                            "value": 4.342944819
                        },
                        "a": {
                            "value": 14.2516247073
                        },
                        "mc": {
                            "value": 4.4
                        }
                    },
                    {
                        "starttime": "2015-05-07T04:00:00",
                        "endtime": "2015-05-07T08:00:00",
                        "numberevents": {
                            "value": 2.4
                        },
                        "hydraulicvol": {
                            "value": 172800.0
                        },
                        "b": {
                            "value": 4.342944819
                        },
                        "a": {
                            "value": 14.2516247073
                        },
                        "mc": {
                            "value": 4.4
                        }
                    },
                    {
                        "starttime": "2015-05-07T08:00:00",
                        "endtime": "2015-05-07T12:00:00",
                        "numberevents": {
                            "value": 2.1
                        },
                        "hydraulicvol": {
                            "value": 151200.0
                        },
                        "b": {
                            "value": 4.342944819
                        },
                        "a": {
                            "value": 14.2516247073
                        },
                        "mc": {
                            "value": 4.4
                        }
                    }
                ]
            }
        }
    }}

JSON_GET_TOO_FEW_EVENTS_TEMPLATE = {
    "data": {
        "id": None,
        "attributes": {
            "status": "ModelError-ModelAdaptor",
            "status_code": 500,
            "warning": "Caught in default model exception handler. "
                       "Too few seismic events found, model will not"
                       " continue."
        }
    }}

JSON_POST_TEMPLATE = {
    "data": {
        "id": None,
        "attributes": {
            "status": "TaskAccepted",
            "status_code": 202
        }
    }}


def return_filepath(filename, **kwargs):
    return os.path.join(dirpath, filename)


def create_json_response(filename, **kwargs):
    with open(os.path.join(dirpath, filename), 'rb') as open_resp:
        resp = BufferedReader(open_resp).read()
    return resp


def create_seismicity_models():
    URL_EM1 = 'http://localhost:5000'
    EM1_SFMWID = 'EM1'
    HOUR_IN_SECS = 3600
    DAY_IN_SECS = 86400
    LOW_EVENT_THRESH = 10

    # NOTE(sarsonl): "em1_training_epoch_duration" is optional and defaults to
    # None in the model if not provided. This means the model trains for the
    # maximum length of time possible from data provided, which is the time
    # between first and last hydraulic sample with with positive topflow.

    base_config = {"em1_training_events_threshold": LOW_EVENT_THRESH,
                   "em1_training_magnitude_bin": 0.1,
                   "em1_threshold_magnitude": 0}

    retval = []

    m = SeismicityModel(
        name='EM1-Day-Training-Low-Event-Threshold',
        config={**base_config,
                **{"em1_training_epoch_duration": DAY_IN_SECS}},
        sfmwid=EM1_SFMWID,
        enabled=True,
        seismicitymodeltemplate=SOURCE_MODEL_TEMPLATE,
        url=URL_EM1)
    retval.append(m)

    m = SeismicityModel(
        name='EM1-Hour-Moving-Window-Low-Event-Threshold',
        config={**base_config,
                **{"em1_training_epoch_duration": HOUR_IN_SECS}},
        sfmwid=EM1_SFMWID,
        seismicitymodeltemplate=SOURCE_MODEL_TEMPLATE,
        enabled=True,
        url=URL_EM1)
    retval.append(m)

    return retval


def create_hazard_model():

    return HazardModel(
        name='default',
        logictreetemplate=LOGIC_TREE_TEMPLATE,
        gmpefile=GMPE_TEMPLATE,
        jobconfigfile=JOB_CONFIG_TEMPLATE,
        enabled=True,
        url="http://localhost:8800")


def parse_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'db_url', type=str, metavar='URL',
        help=('DB URL indicating the database dialect and connection '
              'arguments.'))

    return parser.parse_args()


def create_seismicity_samples(datetimes, a_values, b_values, mc_values):
    samples = []
    for index, starttime in enumerate(datetimes[:-1]):
        endtime = datetimes[index + 1]
        sample = SeismicityPredictionBin(
            starttime=starttime,
            endtime=endtime,
            a_value=a_values[index],
            b_value=b_values[index],
            mc_value=mc_values[index])
        samples.append(sample)
    return samples


def insert_test_data(db_url):

    store = Store(db_url)
    store.init_db()
    # create models
    seismicity_models = create_seismicity_models()
    for m in seismicity_models:
        store.add(m)
    hazard_model = create_hazard_model()

    store.add(hazard_model)
    store.save()

    # FIXME(damb): The project and deserializers are configured without any
    # srid. As a consequence, no transformation is performed when importing
    # data.

    # import seismic catalog
    deserializer = QuakeMLCatalogDeserializer(
        ramsis_proj=RAMSIS_PROJ,
        external_proj=WGS84_PROJ,
        ref_easting=REFERENCE_X,
        ref_northing=REFERENCE_Y,
        transform_func_name='pyproj_transform_to_local_coords')
    with open(os.path.join(dirpath, PATH_SEISMICS), 'rb') as ifd:
        cat = deserializer.load(ifd)

    # import hydraulics
    deserializer = HYDWSBoreholeHydraulicsDeserializer(
        ramsis_proj=RAMSIS_PROJ,
        external_proj=WGS84_PROJ,
        ref_easting=REFERENCE_X,
        ref_northing=REFERENCE_Y,
        transform_func_name='pyproj_transform_to_local_coords')
    for fpath in PATHS_HYDRAULICS:

        with open(os.path.join(dirpath, fpath), 'rb') as ifd:
            well = deserializer.load(ifd)

    # create project
    project = default_project(
        name='basel',
        description='Basel Project 2006',
        starttime=PROJECT_STARTTIME,
        endtime=PROJECT_ENDTIME,
        spatialreference=RAMSIS_PROJ,
        referencepoint_x=REFERENCE_X,
        referencepoint_y=REFERENCE_Y)

    # configure project: project settings
    project.seismiccatalogs = [cat]
    project.wells = [well]

    # create forecast
    fc = default_forecast(store, starttime=FORECAST_STARTTIME,
                          endtime=FORECAST_ENDTIME,
                          num_scenarios=0,
                          name='Basel Forecast')

    fc.project = project
    # add exemplary scenario
    scenario = default_scenario(store, name='Basel Scenario')
    fc.scenarios = [scenario]
    seismicity_stage = scenario[EStage.SEISMICITY]
    seismicity_stage.config = {'prediction_bin_duration': 21600}
    seismicity_stage.status.state = EStatus.COMPLETE
    risk_stage = scenario[EStage.RISK]
    risk_stage.enabled = False
    hazard_stage = scenario[EStage.HAZARD]
    hazard_stage.enabled = True
    hazard_stage.model = hazard_model
    scenario.reservoirgeom = RESERVOIR_INPUT

    deserializer = HYDWSBoreholeHydraulicsDeserializer(
        ramsis_proj=RAMSIS_PROJ,
        external_proj=WGS84_PROJ,
        ref_easting=REFERENCE_X,
        ref_northing=REFERENCE_Y,
        transform_func_name='pyproj_transform_to_local_coords',
        plan=True)
    with open(os.path.join(dirpath, PATH_INJECTION_PLAN), 'rb') as ifd:
        scenario.well = deserializer.load(ifd)

    store.add(project)
    store.add(fc)
    store.add(scenario)
    runids = ["1bcc9e3f-d9bd-4dd2-a626-735cbef419dd",
              "1bcc9e3f-d9bd-4dd2-a626-735cbef41123"]
    starttime = datetime(2006, 12, 8, 8, 45)
    datetimes = [starttime + timedelta(seconds=21600 * x) for x in range(3)]
    a_values = [1.2, 1.5]
    b_values = [1.6, 1.7]
    mc_values = [2.5, 2.5]

    store.save()
    runs = scenario[EStage.SEISMICITY].runs
    for index, seis_run in enumerate(runs):
        seis_run.runid = runids[index]
        samples = create_seismicity_samples(
            datetimes, a_values, b_values, mc_values)
        seis_run.result = ReservoirSeismicityPrediction(
            x_min=X_MIN,
            y_min=Y_MIN,
            z_min=Z_MIN,
            x_max=X_MAX,
            y_max=Y_MAX,
            z_max=Z_MAX,
            samples=samples)
        seis_run.status.state = EStatus.COMPLETE
        store.add(seis_run.result)
        for sample in samples:
            store.add(sample)
    try:
        store.save()
    except Exception:
        store.session.rollback()
        raise
    finally:
        store.session.remove()
        store.engine.dispose()


class MockResponse:
    def __init__(self, status, resp):
        self.status = status
        self.resp = resp
        self.content = self.json()

    def raise_for_status(self):
        pass

    def json(self):
        resp = self.resp
        if isinstance(self.resp, bytes):
            resp = json.loads(copy(self.resp).decode())
        return resp


class MockPostResponse:
    def __init__(self, status, resp):
        self.status = status
        self.resp = resp

    def raise_for_status(self):
        pass

    def json(self):
        resp = json.loads(copy(self.resp).decode())
        return resp


class MockedRequestsPost:
    def __init__(self):
        self.number_run = 1

    def mocked_requests_post(self, *args, **kwargs):
        if args[0] == 'http://localhost:8800/v1/calc/run':
            if self.number_run == 1:
                with open(os.path.join(dirpath, POST_RESPONSE1),
                          'rb') as open_resp:
                    resp = BufferedReader(open_resp).read()
                    self.number_run += 1
                    return MockPostResponse(200, resp)
            elif self.number_run == 2:
                with open(os.path.join(dirpath, POST_RESPONSE2),
                          'rb') as open_resp:
                    resp = BufferedReader(open_resp).read()
                    self.number_run += 1
                    return MockPostResponse(200, resp)
        return MockResponse(404, None)


def mocked_requests_get(*args, **kwargs):

    if args[0] == "http://localhost:8800/v1/calc/result/1031":
        return MockResponse(
            200, return_filepath(XML_RESULTS_BINARY1))
    elif args[0] == "http://localhost:8800/v1/calc/result/1033":
        return MockResponse(
            200, return_filepath(XML_RESULTS_BINARY2))
    elif args[0] == "http://localhost:8800/v1/calc/result/1056":
        return MockResponse(
            200, return_filepath(XML_RESULTS_BINARY_MAPS1))
    elif args[0] == "http://localhost:8800/v1/calc/result/1057":
        return MockResponse(
            200, return_filepath(XML_RESULTS_BINARY_MAPS2))
    elif args[0] == "http://localhost:8800/v1/calc/10/results":
        return MockResponse(
            200, create_json_response(RESPONSE_LIST_BINARY))
    elif args[0] == "http://localhost:8800/v1/calc/10/status":
        return MockResponse(
            200, create_json_response(RESPONSE_STATUS_BINARY))
    elif args[0] == "http://localhost:8800/v1/calc/11/results":
        return MockResponse(
            200, create_json_response(RESPONSE_LIST_BINARY))
    elif args[0] == "http://localhost:8800/v1/calc/11/status":
        return MockResponse(
            200, create_json_response(RESPONSE_STATUS_BINARY))
    return MockResponse(404, None)


def mocked_pyqtsignal(*args, **kwargs):
    return mock.MagicMock()


class MockSignal():
    def emit(self, *args, **kwargs):
        pass


def signal_factory():
    return MockSignal()


def zipfile_archive(arg):
    with open(arg, 'rb') as open_resp:
        resp = zipfile.ZipFile(open_resp)
        infolist = resp.infolist()
        for zipinfo_obj in infolist:
            obj_filename = zipinfo_obj.filename
            yield resp.read(obj_filename).decode()


mocked_requests_post_init = MockedRequestsPost()


class IntegrationTestCase(unittest.TestCase):
    # The default user and password are added by default from the
    # kartoza/postgis image
    DEFAULT_USER = 'docker'
    DEFAULT_HOST = 'localhost'
    DEFAULT_PASSWORD = 'docker'
    DEFAULT_PORT = 5435
    DEFAULT_DBNAME = 'postgres'
    TEST_DBNAME = 'test'
    TEST_USER = 'test'
    TEST_PASSWORD = 'test'
    TMP_DIR = os.path.join(dirpath, 'tmp_dir')

    def postgres_test_url(self):

        return(f'postgresql://{self.TEST_USER}:{self.TEST_PASSWORD}@'
               f'{self.DEFAULT_HOST}:{self.DEFAULT_PORT}/{self.TEST_DBNAME}')

    def setUpSingleGeom(self):
        # Login with default credentials and create a new
        # testing database
        conn0 = psycopg2.connect(
            port=self.DEFAULT_PORT, user=self.DEFAULT_USER,
            host=self.DEFAULT_HOST, password=self.DEFAULT_PASSWORD,
            dbname=self.DEFAULT_DBNAME)
        conn0.autocommit = True
        cursor0 = conn0.cursor()
        cursor0.execute(f"DROP DATABASE IF EXISTS {self.TEST_DBNAME}")
        cursor0.execute(f"DROP USER IF EXISTS {self.TEST_USER}")
        cursor0.execute(f"CREATE USER {self.TEST_USER} with password "
                        f"'{self.TEST_PASSWORD}' SUPERUSER")
        cursor0.execute(f"CREATE DATABASE {self.TEST_DBNAME} with owner "
                        f"{self.TEST_USER}")
        cursor0.execute(
            f"select pg_terminate_backend(pg_stat_activity.pid)"
            " from pg_stat_activity where pg_stat_activity.datname="
            "'{self.TEST_DBNAME}' AND pid <> pg_backend_pid()")
        cursor0.close()
        conn0.close()
        conn = psycopg2.connect(
            host=self.DEFAULT_HOST, port=self.DEFAULT_PORT,
            user=self.TEST_USER, password=self.TEST_PASSWORD,
            dbname=self.TEST_DBNAME)
        cursor = conn.cursor()
        cursor.execute(f"CREATE EXTENSION IF NOT EXISTS postgis;")
        cursor.close()
        conn.commit()
        conn.close()
        insert_test_data(self.postgres_test_url())

    def tearDown(self):
        # Login with default credentials and create a new
        # testing database
        conn0 = psycopg2.connect(
            port=self.DEFAULT_PORT, user=self.DEFAULT_USER,
            host=self.DEFAULT_HOST, password=self.DEFAULT_PASSWORD,
            dbname=self.DEFAULT_DBNAME)
        conn0.autocommit = True
        cursor0 = conn0.cursor()
        # Sometimes not all connctions close successfully so force close them.
        cursor0.execute(
            f"select pg_terminate_backend(pg_stat_activity.pid)"
            " from pg_stat_activity where pg_stat_activity.datname="
            "'{self.TEST_DBNAME}' AND pid <> pg_backend_pid()")
        cursor0.execute(f"DROP DATABASE IF EXISTS {self.TEST_DBNAME}")
        cursor0.close()
        conn0.close()
        if not os.path.exists(self.TMP_DIR):
            os.mkdir(self.TMP_DIR)

    def connect_ramsis(self):
        app = mock.Mock(app_settings={'data_dir': self.TMP_DIR})
        controller = Controller(app, LaunchMode.LAB, )
        controller.connect(self.postgres_test_url())

        store = controller.store
        return controller, store

    @mock.patch('RAMSIS.core.engine.engine.HazardHandler.'
                'execution_status_update', side_effect=signal_factory)
    @mock.patch('RAMSIS.core.worker.oq_hazard.requests.get',
                side_effect=mocked_requests_get)
    @mock.patch('RAMSIS.core.worker.oq_hazard.requests.post',
                side_effect=mocked_requests_post_init.mocked_requests_post)
    @mock.patch('RAMSIS.io.oq_hazard.'
                'OQHazardOMessageDeserializer._read_ziparchive',
                side_effect=zipfile_archive)
    def test_successful_hazard_flow(self,
                                    mock_ziparchive,
                                    mock_post,
                                    mock_get,
                                    mock_signal):
        """
        Test the flow with only the seismicity & hazard stage enabled
        and seismicity stage complete.
        """
        self.setUpSingleGeom()
        self.maxDiff = None
        controller, store = self.connect_ramsis()
        forecast = store.session.query(Forecast).first()
        forecast.status.state = EStatus.RUNNING

        scenario = forecast.scenarios[0]
        scenario.status.state = EStatus.RUNNING

        seismicity_stage = scenario[EStage.SEISMICITY]
        seismicity_stage.status.state = EStatus.COMPLETE

        hazard_stage = scenario[EStage.HAZARD]
        hazard_stage.status.state = EStatus.PENDING

        risk_stage = scenario[EStage.RISK]
        risk_stage.enabled = False

        seis_model_runs = seismicity_stage.runs
        for run in seis_model_runs:
            run.status.state = EStatus.COMPLETE

        # Set up geopoints
        #geopoint1 = store.session.add(GeoPoint(lat=47.5580339199014, lon=7.56698854824407))

        store.save()
        project = store.session.query(Project).first()
        forecast = store.session.query(Forecast).first()
        controller.open_project(project)
        store.session.close()
        controller.engine.run(datetime(2006, 12, 2), forecast.id)
        # Allow main thread to wait until other threads triggered by
        # workflow complete for 200 seconds maximum
        for i in range(50):
            forecast_status = store.session.query(Forecast).first().\
                status.state
            store.session.close()
            ##self.assertNotEqual(forecast_status, EStatus.ERROR)
            if forecast_status == EStatus.COMPLETE:
                print("forecast COMPLETEV")
                break
            time.sleep(4)

        # Check pyqtsignals that were produced
        signal_list = mock_signal.emit.call_args_list
        self.assertEqual(len(signal_list), 5)
        for call_tuple in signal_list:
            prefect_status = call_tuple[0][0][0]
            self.assertTrue(prefect_status.message in ["Task run succeeded.", "All reference tasks succeeded."])
            self.assertTrue(prefect_status.is_successful())

            parent_type = call_tuple[0][0][1]
            self.assertTrue(parent_type in [
                type(HazardModelRun()), type(HazardStage())])

        # Check data send to remote worker
        posted_data = mock_post.call_args_list[0][1]
        posted_data2 = mock_post.call_args_list[1][1]

        self.assertEqual(len(
            posted_data['files']), 5)
        self.assertEqual(len(
            posted_data2['files']), 5)

        # Check that forecast, scenario and model runs all have completed
        non_stage_statuses = store.session.query(Status).\
            filter(Status.stage_id is None).all()
        self.assertTrue(
            all([s.state == EStatus.COMPLETE
                 for s in non_stage_statuses]))
        # Check that the seismicity stage has completed.
        forecast = store.session.query(Forecast).first()
        stage = forecast.scenarios[0][EStage.HAZARD]
        self.assertEqual(stage.status.state, EStatus.COMPLETE)

        # Check number of samples produced in total
        pointvalues_list = [run.hazardpointvalues for run in stage.runs]
        pointvalues = [value for sublist in pointvalues_list for value
                       in sublist]
        self.assertEqual(len(pointvalues), 3264)
        curves_list = [run.hazardcurves for run in stage.runs]
        curves = [value for sublist in curves_list for value in sublist]
        self.assertEqual(len(curves), 272)

        geopoints = [(point.geopoint.lat, point.geopoint.lon)
                     for point in pointvalues]
        geopoints = sorted(set(geopoints))
        # rewrite geopoints file in case results are altered
        #with open(os.path.join(dirpath, GEOPOINTS), 'w') as geopoints_read: # noqa
        #    for tup in geopoints:
        #        lat, lon = tup
        #        geopoints_read.write(f"{lat} {lon}\n")
        with open(os.path.join(dirpath, GEOPOINTS), 'r') as geopoints_read:
            geopoint_lines = geopoints_read.readlines()
        geopoints_stored = []

        for line in geopoint_lines:
            lat_str, lon_str = line.split()
            geopoints_stored.append((float(lat_str), float(lon_str)))

        geopoints_stored = sorted(set(geopoints_stored))
        self.assertEqual(geopoints, geopoints_stored)
        store.session.remove()
        store.engine.dispose()


if __name__ == "__main__":
    unittest.main()
