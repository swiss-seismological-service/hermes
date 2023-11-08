# For giving traceback from typer results:
# traceback.print_exception(*result.exc_info)
from sqlalchemy import select
from typer.testing import CliRunner
import json
import logging

from ramsis.datamodel import ForecastSeries, Project, ModelConfig, \
    Forecast
from os.path import dirname, abspath, join

from RAMSIS.tests.utils import load_model, \
    create_project, create_forecastseries, MockResponse

logger = logging.getLogger(__name__)

runner = CliRunner(echo_stdin=True)
dirpath = join(dirname(abspath(__file__)), '..')

#  URLs are same as in bedretto project config
FDSNWS_URL = "http://scforge.ethz.ch:8080/fdsnws/event/1/query?" \
    "minmagnitude=-7&contributor=GES_Forge22"
HYDWS_URL = "http://scforge.ethz.ch:8081/hydws/v1/boreholes/"\
    "c21pOmNoLmV0aHouc2VkL2JoLzE2QS0zMg==?level=hydraulic"

model_requests_path = join(dirpath, 'model_requests')

model_request_1 = 'model_request_induced_1.json'

model_response_path = join(dirpath, 'results')

resources_path = join(dirpath, 'resources')
hyd_path = join(
    resources_path, '2022-04-21_hydws.json')
inj_plan_path = join(
    resources_path, '16A-32_forge_2022_04_21_plan.json')
cat_path = join(
    resources_path, '2022-04-21_fdsn_catalog.xml')
model_config_path = join(
    resources_path, 'model_forge_2022.json')
project_config_path = join(
    resources_path, 'project_forge_2022.json')
forecast_config_path = join(
    resources_path, 'forecast_forge_2022.json')


def mocked_requests_delete(*args, **kwargs):
    return MockResponse([], 200)


def mocked_requests_post(*args, **kwargs):
    logger.debug(f"Input to mocked_requests_post: {args}")
    if 'v1/sfm/run' in args[0]:
        model_response_to_post_induced_1_path = join(
            model_response_path, 'model_response_to_post_induced_1.json')
        with open(model_response_to_post_induced_1_path, "r") as f:
            model_response_to_post_induced_1_data = json.load(f)
        return MockResponse(model_response_to_post_induced_1_data, 200)
    else:
        logger.warning("haven't caught request")
    return MockResponse(None, 404)


def mocked_sfm_get(*args, **kwargs):
    if 'v1/sfm/run/'\
            '02d24be2-1f6b-4fc3-8fd3-a83ab5875932' in args[0]:
        model_request_induced_1_path = join(
            model_response_path, "model_response_induced_1.json")
        with open(model_request_induced_1_path, "r") as f:
            model_response_induced_1_data = json.load(f)
        return MockResponse(model_response_induced_1_data, 200)
    return MockResponse(None, 404)


def mocked_datasources_get(*args, **kwargs):
    if args[0] == FDSNWS_URL:
        with open(cat_path, "rb") as f:
            data = f.read()
        return MockResponse({}, 200, data)
    elif args[0] == HYDWS_URL:
        with open(hyd_path, "rb") as f:
            data = f.read()
        return MockResponse({}, 200, data)
    elif 'v1/sfm/run/'\
            '02d24be2-1f6b-4fc3-8fd3-a83ab5875932' in args[0]:
        model_request_induced_1_path = join(
            model_response_path, "model_response_induced_1.json")
        with open(model_request_induced_1_path, "r") as f:
            model_response_induced_1_data = json.load(f)
        return MockResponse(model_response_induced_1_data, 200)
    return MockResponse(None, 404)


class TestMultiForgeCase:
    """ End to end test for the forecast flow with forge data.
    """
    def test_forge_flow(self, mocker, session, use_ws):
        # Setup test --------
        _ = load_model(model_config_path)
        models = session.execute(
            select(ModelConfig)).scalars().all()
        assert len(models) == 1
        create_project(project_config_path, well_data=hyd_path)
        projects = session.execute(
            select(Project)).scalars().all()
        assert len(projects) == 1

        create_forecastseries(forecast_config_path, "1")
        forecastseries = session.execute(
            select(ForecastSeries)).scalars().all()
        assert len(forecastseries) == 1
        # -------------------

        from RAMSIS.db import db_url
        from RAMSIS.flows.forecast import scheduled_ramsis_flow
        if not use_ws:
            print("patching requests")
            mock_get_data = mocker.patch('RAMSIS.clients.datasources.get')
            mock_get_data.side_effect = mocked_datasources_get
            mock_get_data = mocker.patch('RAMSIS.clients.sfm.get')
            mock_get_data.side_effect = mocked_sfm_get
            mock_post = mocker.patch('RAMSIS.clients.sfm.post')
            mock_post.side_effect = mocked_requests_post
            mock_post = mocker.patch('RAMSIS.clients.sfm.delete')
            mock_post.side_effect = mocked_requests_delete
        forecastseries = session.execute(
            select(ForecastSeries)).scalars().first()
        _ = scheduled_ramsis_flow(
            forecastseries.id, db_url,
            forecastseries.starttime.strftime('%Y-%m-%dT%H:%M:%S'))
        forecast = session.execute(
            select(Forecast)).scalars().one()
        timebins = forecast.runs[0].resulttimebins
        assert len(timebins) == 23
        for timebin in timebins[0:11]:
            assert len(timebin.seismicforecastgrids) == 1
            assert len(timebin.seismicforecastgrids[0].seismicrates) == 1
        for timebin in timebins[11:23]:
            assert len(timebin.seismicforecastgrids) == 10
            assert len(timebin.seismicforecastgrids[0].seismicrates) == 1

        # Make the test fail to see full output
        # assert 0 == 1
