# For giving traceback from typer results:
# traceback.print_exception(*result.exc_info)
from sqlalchemy import select
import pytest
from typer.testing import CliRunner
# import json
import logging

from ramsis.datamodel import ForecastSeries, Project, ModelConfig, \
    Forecast
from os.path import dirname, abspath, join

from RAMSIS.tests.utils import load_model, \
    create_project, create_forecastseries

logger = logging.getLogger(__name__)

runner = CliRunner(echo_stdin=True)
dirpath = dirname(abspath(__file__))

#  URLs are same as in bedretto project config
# FDSNWS_URL = "http://bedretto-dev.ethz.ch:8080/fdsnws/event/1/query" \
#     "?minmagnitude=-7"
# HYDWS_URL = "http://inducat.ethz.ch:8080/hydws/v1/boreholes" \
#     "/c21pOmNoLmV0aHouc2VkL2JoL1NUMQ==?level=hydraulic"

model_requests_path = join(dirpath, 'model_requests')

model_request_1 = 'model_request_induced_1.json'

model_response_path = join(dirpath, 'results')

resources_path = join(dirpath, 'resources')
inj_plan_path = join(
    resources_path, '16A-32_forge_2022_04_21.json')
model_config_path = join(
    resources_path, 'model_forge_2022.json')
project_config_path = join(
    resources_path, 'project_forge_2022.json')
forecast_config_path = join(
    resources_path, 'forecast_forge_2022.json')
# fdsn_catalog_path = join(
#     resources_path, '2022-06-22_fdsn_catalog.xml')
# hyd_path = join(
#     resources_path, '2022-06-22_hydws.json')


# def mocked_requests_post(*args, **kwargs):
#     logger.debug(f"Input to mocked_requests_post: {args}")
#     if 'v1/sfm/models/em1/run' in args[0]:
#         model_response_to_post_induced_1_path = join(
#             model_response_path, 'model_response_to_post_induced_1.json')
#         with open(model_response_to_post_induced_1_path, "r") as f:
#             model_response_to_post_induced_1_data = json.load(f)
#         return MockResponse(model_response_to_post_induced_1_data, 200)
#     else:
#         logger.warning("haven't caught request")
#     return MockResponse(None, 404)


# def mocked_datasources_get(*args, **kwargs):
#     if args[0] == FDSNWS_URL:
#         with open(fdsn_catalog_path, "rb") as f:
#             data = f.read()
#         return MockResponse({}, 200, data)
#     elif args[0] == HYDWS_URL:
#         with open(hyd_path, "rb") as f:
#             data = f.read()
#         return MockResponse({}, 200, data)
#     elif 'v1/sfm/models/em1/run/'\
#             '1bcc9e3f-d9bd-4dd2-a626-735cbef419dd' in args[0]:
#         model_request_induced_1_path = join(
#             model_response_path, "model_response_induced_1.json")
#         with open(model_request_induced_1_path, "r") as f:
#             model_response_induced_1_data = json.load(f)
#         return MockResponse(model_response_induced_1_data, 200)
#     return MockResponse(None, 404)


class TestInducedForgeCase:
    def test_ramsis_forge_setup(self, mocker, session):
        _ = load_model(model_config_path)
        models = session.execute(
            select(ModelConfig)).scalars().all()
        assert len(models) == 1
        create_project(project_config_path, well_data=inj_plan_path)
        projects = session.execute(
            select(Project)).scalars().all()
        assert len(projects) == 1

        create_forecastseries(forecast_config_path, "1")
        forecastseries = session.execute(
            select(ForecastSeries)).scalars().all()
        assert len(forecastseries) == 1

    @pytest.mark.run(after='test_ramsis_forge_setup')
    def test_run_forge_forecast(self, mocker, session):
        from RAMSIS.cli import ramsis_app as app # noqa
        from RAMSIS.db import db_url
        from RAMSIS.flows.forecast import scheduled_ramsis_flow
        # mock_get = mocker.patch('RAMSIS.core.datasources.requests.get')
        # mock_get.side_effect = mocked_datasources_get_etas
        forecastseries = session.execute(
            select(ForecastSeries)).scalars().first()
        _ = scheduled_ramsis_flow(
            forecastseries.id, db_url,
            forecastseries.starttime.strftime('%Y-%m-%dT%H:%M:%S'))
        forecast = session.execute(
            select(Forecast)).scalars().one()
        timebins = forecast.runs[0].resulttimebins
        assert len(timebins) == 33
        for timebin in timebins[0:5]:
            assert len(timebin.seismicforecastgrids) == 1
            assert len(timebin.seismicforecastgrids[0].seismicrates) == 1
        for timebin in timebins[5:33]:
            assert len(timebin.seismicforecastgrids) == 10
            assert len(timebin.seismicforecastgrids[0].seismicrates) == 1

        # Make the test fail to see full output
        # assert 0 == 1
