"""
test_forecast_flow.py

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
import unittest
from unittest import mock
import time
import os
import psycopg2
import argparse
import json

from datetime import datetime

from ramsis.datamodel.forecast import (  # noqa
    Forecast, ForecastScenario, ForecastStage, SeismicityForecastStage,
    SeismicitySkillStage, HazardStage, RiskStage, EStage)
from ramsis.datamodel.hydraulics import (  # noqa
    Hydraulics, InjectionPlan, HydraulicSample)
from ramsis.datamodel.model import Model, ModelRun  # noqa
from ramsis.datamodel.project import Project  # noqa
from ramsis.datamodel.seismicity import (  # noqa
    SeismicityModel, SeismicityModelRun, ReservoirSeismicityPrediction,
    SeismicityPredictionBin)
from ramsis.datamodel.seismics import SeismicCatalog, SeismicEvent  # noqa
from ramsis.datamodel.settings import ProjectSettings  # noqa
from ramsis.datamodel.status import Status, EStatus  # noqa
from ramsis.datamodel.well import InjectionWell, WellSection  # noqa

from RAMSIS.core.builder import (
    default_project, default_forecast, default_scenario)
from RAMSIS.core.controller import Controller, LaunchMode
from RAMSIS.core.store import Store
from RAMSIS.io.hydraulics import HYDWSBoreholeHydraulicsDeserializer
from RAMSIS.io.seismics import QuakeMLCatalogDeserializer

dirpath = os.path.dirname(os.path.abspath(__file__))

RAMSIS_PROJ = ("+proj=utm +zone=32N +ellps=WGS84 +datum=WGS84 +units=m "
               "+x_0=0.0 +y_0=0.0 +no_defs")
WGS84_PROJ = "epsg:4326"
REFERENCE_X = 681922
REFERENCE_Y = 1179229

PATH_SEISMICS = 'catalog_data/seismics.qml'
# Only ~this many files can be imported and merged before
# memory error occurs.
PATHS_HYDRAULICS = [
    'hyd_data/basel-2006-01.json']

PATH_INJECTION_PLAN = 'injection_data/injectionplan-mignan.json'

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

JSON_POSTED_DATA1 = 'results_data/json_posted_data1.json'
JSON_POSTED_DATA2 = 'results_data/json_posted_data2.json'

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


def create_json_response(task_id, response_template, **kwargs):
    resp = response_template.copy()
    resp['data']['id'] = task_id
    return resp


def create_models():
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
        url=URL_EM1)
    retval.append(m)

    m = SeismicityModel(
        name='EM1-Hour-Moving-Window-Low-Event-Threshold',
        config={**base_config,
                **{"em1_training_epoch_duration": HOUR_IN_SECS}},
        sfmwid=EM1_SFMWID,
        enabled=True,
        url=URL_EM1)
    retval.append(m)

    return retval


def parse_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'db_url', type=str, metavar='URL',
        help=('DB URL indicating the database dialect and connection '
              'arguments.'))

    return parser.parse_args()


def insert_test_data(db_url):

    store = Store(db_url)
    store.init_db()
    # create models
    models = create_models()
    for m in models:
        store.add(m)
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
        spatialreference=WGS84_PROJ,
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
    seismicity_stage.config = {'prediction_bin_duration': 7200}
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
    try:
        store.save()
    except Exception:
        store.session.rollback()
        raise
    finally:
        store.session.remove()
        store.engine.dispose()


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self.json_data


def mocked_requests_post(*args, **kwargs):
    training_epoch = (json.loads(kwargs['data'])['data']['attributes']
                      ['model_parameters']
                      ['em1_training_epoch_duration'])
    if args[0] == 'http://localhost:5000/v1/EM1/runs':
        if training_epoch == 3600:
            return MockResponse(
                create_json_response("1bcc9e3f-d9bd-4dd2-a626-735cbef419dd",
                                     JSON_POST_TEMPLATE),
                200)
        elif training_epoch == 86400:
            return MockResponse(
                create_json_response("1bcc9e3f-d9bd-4dd2-a626-735cbef41123",
                                     JSON_POST_TEMPLATE),
                200)
    elif args[0] == 'http://localhost:5000':
        return MockResponse({"key2": "value2"}, 200)

    return MockResponse(None, 404)


def mocked_requests_get(*args, **kwargs):

    if args[0] == 'http://localhost:5000/v1/EM1/runs/'\
            '1bcc9e3f-d9bd-4dd2-a626-735cbef419dd':
        return MockResponse(
            create_json_response("1bcc9e3f-d9bd-4dd2-a626-735cbef419dd",
                                 JSON_GET_TEMPLATE), 200)
    elif args[0] == 'http://localhost:5000/v1/EM1/runs/'\
            '1bcc9e3f-d9bd-4dd2-a626-735cbef41123':
        return MockResponse(
            create_json_response("1bcc9e3f-d9bd-4dd2-a626-735cbef41123",
                                 JSON_GET_TEMPLATE), 200)
    return MockResponse(None, 404)


def mocked_requests_get_error(*args, **kwargs):

    if args[0] == 'http://localhost:5000/v1/EM1/runs/'\
            '1bcc9e3f-d9bd-4dd2-a626-735cbef419dd':
        return MockResponse(
            create_json_response("1bcc9e3f-d9bd-4dd2-a626-735cbef419dd",
                                 JSON_GET_TOO_FEW_EVENTS_TEMPLATE), 200)
    elif args[0] == 'http://localhost:5000/v1/EM1/runs/'\
            '1bcc9e3f-d9bd-4dd2-a626-735cbef41123':
        return MockResponse(
            create_json_response("1bcc9e3f-d9bd-4dd2-a626-735cbef41123",
                                 JSON_GET_TOO_FEW_EVENTS_TEMPLATE), 200)
    return MockResponse(None, 404)


def mocked_pyqtsignal(*args, **kwargs):
    return mock.MagicMock()


class MockSignal():
    def emit(self, *args, **kwargs):
        pass


def signal_factory():
    return MockSignal()


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

    def postgres_test_url(self):

        return(f'postgresql://{self.TEST_USER}:{self.TEST_PASSWORD}@'
               f'{self.DEFAULT_HOST}:{self.DEFAULT_PORT}/{self.TEST_DBNAME}')

    def setUp(self):
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
            "'{self.TEST_DBNAME}'")
        cursor0.close()
        conn0.close()

    def connect_ramsis(self):
        controller = Controller(mock.MagicMock(), LaunchMode.LAB)
        controller.connect(self.postgres_test_url())

        store = controller.store
        return controller, store

    @mock.patch('RAMSIS.core.engine.engine.ForecastHandler.'
                'execution_status_update', side_effect=signal_factory)
    @mock.patch('RAMSIS.core.worker.sfm.requests.get',
                side_effect=mocked_requests_get)
    @mock.patch('RAMSIS.core.worker.sfm.requests.post',
                side_effect=mocked_requests_post)
    def test_successful_seismicity_flow(self, mock_post, mock_get,
                                        mock_signal):
        """
        Test the flow with only the seismicity stage enabled and two models
        enabled.
        """
        self.maxDiff = None
        controller, store = self.connect_ramsis()
        statuses = store.session.query(Status).all()
        for item_status in statuses:
            item_status.state = EStatus.PENDING

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
            self.assertNotEqual(forecast_status, EStatus.ERROR)
            if forecast_status == EStatus.COMPLETE:
                break
            time.sleep(2)

        # Check pyqtsignals that were produced
        signal_list = mock_signal.emit.call_args_list
        self.assertEqual(len(signal_list), 4)
        for call_tuple in signal_list:
            prefect_status = call_tuple[0][0][0]
            self.assertEqual(prefect_status.message, "Task run succeeded.")
            self.assertTrue(prefect_status.is_successful())

            parent_type = call_tuple[0][0][1]
            self.assertEqual(parent_type, type(SeismicityModelRun()))

        # Check data send to remote worker
        posted_data = mock_post.call_args_list[0][1]['data']
        posted_data2 = mock_post.call_args_list[1][1]['data']

        with open(os.path.join(dirpath, JSON_POSTED_DATA1), 'r') as json_d:
            json_data = json.load(json_d)
        with open(os.path.join(dirpath, JSON_POSTED_DATA2), 'r') as json_d:
            json_data2 = json.load(json_d)
        # As we are not sure which order the models are processed,
        # we cannot be sure which status is produced first
        if (json.loads(posted_data)["data"]["attributes"]["model_parameters"]
                ["em1_training_epoch_duration"] == 86400):
            self.assertEqual(posted_data, json_data)
            self.assertEqual(posted_data2, json_data2)
        else:
            self.assertEqual(posted_data, json_data2)
            self.assertEqual(posted_data2, json_data)

        # Check that forecast, scenario and model runs all have completed
        non_stage_statuses = store.session.query(Status).\
            filter(Status.stage_id is None).all()
        self.assertTrue(
            all([s.state == EStatus.COMPLETE
                 for s in non_stage_statuses]))
        # Check that the seismicity stage has completed.
        forecast = store.session.query(Forecast).first()
        stage = forecast.scenarios[0][EStage.SEISMICITY]
        self.assertEqual(stage.status.state, EStatus.COMPLETE)

        # Check number of samples produced in total
        results = [run.result for run in stage.runs]
        self.assertEqual(len(results), 2)
        bins_nested = [res.samples for res in results]
        bins = [item for sublist in bins_nested for item in sublist]
        self.assertEqual(len(bins), 6)
        # Check the content of the results
        self.assertEqual(results[0].x_min, X_MIN)
        self.assertEqual(results[0].x_max, X_MAX)
        self.assertEqual(results[0].y_min, Y_MIN)
        self.assertEqual(results[0].y_max, Y_MAX)
        self.assertEqual(results[0].z_min, Z_MIN)
        self.assertEqual(results[0].z_max, Z_MAX)

        bin_starttimes = [item.starttime for item in bins]
        self.assertEqual(sorted(bin_starttimes), [
            datetime(2015, 5, 7),
            datetime(2015, 5, 7),
            datetime(2015, 5, 7, 4),
            datetime(2015, 5, 7, 4),
            datetime(2015, 5, 7, 8),
            datetime(2015, 5, 7, 8)])

        bin_endtimes = [item.endtime for item in bins]
        self.assertEqual(sorted(bin_endtimes), [
            datetime(2015, 5, 7, 4),
            datetime(2015, 5, 7, 4),
            datetime(2015, 5, 7, 8),
            datetime(2015, 5, 7, 8),
            datetime(2015, 5, 7, 12),
            datetime(2015, 5, 7, 12)])

        bin_events = [item.numberevents_value for item in bins]
        self.assertEqual(sorted(bin_events), sorted([
            1.8, 1.8, 2.1, 2.1, 2.4, 2.4]))
        bin_a = [item.a_value for item in bins]
        self.assertTrue(all(item == 14.2516247073 for item in bin_a))

        bin_b = [item.b_value for item in bins]
        self.assertTrue(all(item == 4.342944819 for item in bin_b))

        bin_mc = [item.mc_value for item in bins]
        self.assertTrue(all(item == 4.4 for item in bin_mc))
        store.session.remove()
        store.engine.dispose()

    @mock.patch('RAMSIS.core.engine.engine.ForecastHandler.'
                'execution_status_update', side_effect=signal_factory)
    @mock.patch('RAMSIS.core.worker.sfm.requests.get',
                side_effect=mocked_requests_get_error)
    @mock.patch('RAMSIS.core.worker.sfm.requests.post',
                side_effect=mocked_requests_post)
    def test_model_error(self, mock_post, mock_get, mock_signal):
        """
        Test workflow when an Error is returned in the get
        request from remote worker.
        """
        controller, store = self.connect_ramsis()
        statuses = store.session.query(Status).all()
        for item_status in statuses:
            item_status.state = EStatus.PENDING

        store.save()
        project = store.session.query(Project).first()
        forecast = store.session.query(Forecast).first()
        controller.open_project(project)
        store.session.close()

        controller.engine.run(datetime(2006, 12, 2), forecast.id)
        # Allow main thread to wait until other threads triggered by
        # workflow complete for 200 seconds maximum
        for i in range(10):
            forecast_status = store.session.query(Forecast).first().\
                status.state
            store.session.close()
            if forecast_status == EStatus.ERROR:
                break
            time.sleep(5)

        # Check that forecast, scenario and model all have an error status
        non_stage_statuses = store.session.query(Status).\
            filter(Status.stage_id is None).all()
        self.assertTrue(all([s.state == EStatus.ERROR
                             for s in non_stage_statuses]))
        # Check that the seismicity stage has completed.
        forecast = store.session.query(Forecast).first()
        stage = forecast.scenarios[0][EStage.SEISMICITY]
        self.assertEqual(stage.status.state, EStatus.ERROR)

        # Check pyqtsignals that were produced
        signal_list = mock_signal.emit.call_args_list
        self.assertEqual(len(signal_list), 4)
        for i, call_tuple in enumerate(signal_list):
            prefect_status = call_tuple[0][0][0]
            if i in [0, 1]:
                self.assertEqual(prefect_status.message, "Task run succeeded.")
                self.assertTrue(prefect_status.is_successful())
            elif i in [2, 3]:
                self.assertTrue(prefect_status.message in ["Remote Seismicity Model Worker has returned an unsuccessful status code.(runid=1bcc9e3f-d9bd-4dd2-a626-735cbef419dd: OrderedDict([('data', OrderedDict([('id', UUID('1bcc9e3f-d9bd-4dd2-a626-735cbef419dd')), ('attributes', OrderedDict([('status', 'ModelError-ModelAdaptor'), ('status_code', 500), ('warning', 'Caught in default model exception handler. Too few seismic events found, model will not continue.')]))]))]))", "Remote Seismicity Model Worker has returned an unsuccessful status code.(runid=1bcc9e3f-d9bd-4dd2-a626-735cbef41123: OrderedDict([('data', OrderedDict([('id', UUID('1bcc9e3f-d9bd-4dd2-a626-735cbef41123')), ('attributes', OrderedDict([('status', 'ModelError-ModelAdaptor'), ('status_code', 500), ('warning', 'Caught in default model exception handler. Too few seismic events found, model will not continue.')]))]))]))"]) # noqa
                self.assertTrue(prefect_status.is_failed())

            parent_type = call_tuple[0][0][1]
            self.assertEqual(parent_type, type(SeismicityModelRun()))
        store.session.remove()
        store.engine.dispose()

    @mock.patch('RAMSIS.core.engine.engine.ForecastHandler.'
                'execution_status_update', side_effect=signal_factory)
    @mock.patch('RAMSIS.core.worker.sfm.requests.get',
                side_effect=mocked_requests_get)
    @mock.patch('RAMSIS.core.worker.sfm.requests.post',
                side_effect=mocked_requests_post)
    def test_models_already_dispatched(self, mock_post, mock_get, mock_signal):
        self.execution_statuses = []
        controller, store = self.connect_ramsis()

        model_runs = store.session.query(SeismicityModelRun).all()
        model_run_ids = zip(model_runs, [
            "1bcc9e3f-d9bd-4dd2-a626-735cbef41123",
            "1bcc9e3f-d9bd-4dd2-a626-735cbef419dd"])
        for model_run, runid in model_run_ids:
            model_run.runid = runid

        statuses = store.session.query(Status).all()
        for item_status in statuses:
            if item_status.run_id is not None:
                item_status.state = EStatus.DISPATCHED
            else:
                item_status.state = EStatus.PENDING

        store.save()
        project = store.session.query(Project).first()
        forecast = store.session.query(Forecast).first()
        controller.open_project(project)
        store.session.close()
        controller.engine.run(datetime(2006, 12, 2), forecast.id)
        # workflow complete for 200 seconds maximum
        for i in range(50):
            forecast_status = store.session.query(Forecast).first().\
                status.state
            store.session.close()
            self.assertNotEqual(forecast_status, EStatus.ERROR)
            if forecast_status == EStatus.COMPLETE:
                break
            time.sleep(2)

        # Check pyqtsignals that were produced
        signal_list = mock_signal.emit.call_args_list
        self.assertEqual(len(signal_list), 2)
        for call_tuple in signal_list:
            prefect_status = call_tuple[0][0][0]
            self.assertEqual(prefect_status.message,
                             "Task run succeeded.")
            self.assertTrue(prefect_status.is_successful())

            parent_type = call_tuple[0][0][1]
            self.assertEqual(parent_type, type(SeismicityModelRun()))

        # Check that no POST requests were made
        mock_post.assert_not_called()

        # Check that forecast, scenario and model runs all have completed
        non_stage_statuses = store.session.query(Status).\
            filter(Status.stage_id is None).all()
        self.assertTrue(all([s.state == EStatus.COMPLETE
                             for s in non_stage_statuses]))

        # Check that the seismicity stage has completed.
        forecast = store.session.query(Forecast).first()
        stage = forecast.scenarios[0][EStage.SEISMICITY]
        self.assertEqual(stage.status.state, EStatus.COMPLETE)

        # Check number of samples produced in total
        results = [run.result for run in stage.runs]
        self.assertEqual(len(results), 2)
        bins_nested = [res.samples for res in results]
        bins = [item for sublist in bins_nested for item in sublist]
        self.assertEqual(len(bins), 6)
        store.session.remove()
        store.engine.dispose()

    @mock.patch('RAMSIS.core.engine.engine.ForecastHandler.'
                'execution_status_update', side_effect=signal_factory)
    @mock.patch('RAMSIS.core.worker.sfm.requests.get',
                side_effect=mocked_requests_get)
    @mock.patch('RAMSIS.core.worker.sfm.requests.post',
                side_effect=mocked_requests_post)
    def test_one_model_already_dispatched(self, mock_post, mock_get,
                                          mock_signal):
        controller, store = self.connect_ramsis()
        statuses = store.session.query(Status).all()

        model_runs = store.session.query(SeismicityModelRun).all()
        for model_run in model_runs:
            if model_run.model.id == 1:
                model_run.runid = "1bcc9e3f-d9bd-4dd2-a626-735cbef41123"
                model_run.status.state = EStatus.DISPATCHED
            else:
                model_run.status.state = EStatus.PENDING

        # Alter so that only one model is dispatched.
        for item_status in statuses:
            if item_status.run_id is None:
                item_status.state = EStatus.PENDING

        store.save()
        project = store.session.query(Project).first()
        forecast = store.session.query(Forecast).first()
        controller.open_project(project)
        store.session.close()
        controller.engine.run(datetime(2006, 12, 2), forecast.id)
        # workflow complete for 200 seconds maximum
        for i in range(5):
            forecast_status = store.session.query(Forecast).first().\
                status.state
            store.session.close()
            self.assertNotEqual(forecast_status, EStatus.ERROR)
            if forecast_status == EStatus.COMPLETE:
                break
            time.sleep(10)

        # Check pyqtsignals that were produced
        signal_list = mock_signal.emit.call_args_list
        self.assertEqual(len(signal_list), 3)
        for call_tuple in signal_list:
            prefect_status = call_tuple[0][0][0]
            self.assertEqual(prefect_status.message,
                             "Task run succeeded.")
            self.assertTrue(prefect_status.is_successful())

            parent_type = call_tuple[0][0][1]
            self.assertEqual(parent_type, type(SeismicityModelRun()))

        # Check that only one POST request was made, as only one
        # model is pending
        mock_post.assert_called_once()
        self.assertEqual(mock_get.call_count, 2)

        # Check that forecast, scenario and model runs all have completed
        non_stage_statuses = store.session.query(Status).\
            filter(Status.stage_id is None).all()
        self.assertTrue(all([s.state == EStatus.COMPLETE
                             for s in non_stage_statuses]))

        # Check that the seismicity stage has completed.
        forecast = store.session.query(Forecast).first()
        stage = forecast.scenarios[0][EStage.SEISMICITY]
        self.assertEqual(stage.status.state, EStatus.COMPLETE)

        # Check number of samples produced in total
        results = [run.result for run in stage.runs]
        self.assertEqual(len(results), 2)
        bins_nested = [res.samples for res in results]
        bins = [item for sublist in bins_nested for item in sublist]
        self.assertEqual(len(bins), 6)
        store.session.remove()
        store.engine.dispose()


if __name__ == "__main__":
    unittest.main()
