# For giving traceback from typer results:
# traceback.print_exception(*result.exc_info)
from sqlalchemy import select
import pytest
from typer.testing import CliRunner
import json
import logging
from datetime import datetime
from prefect.testing.utilities import prefect_test_harness

from ramsis.datamodel import ForecastSeries, Project
from os.path import dirname, abspath, join

from RAMSIS.tests.utils import check_updated_model, \
    create_project, create_forecastseries, \
    MockResponse, check_one_forecastseries_in_db, \
    get_forecastseries

logger = logging.getLogger(__name__)

runner = CliRunner(echo_stdin=True)
dirpath = dirname(abspath(__file__))

# URLs are same as in bedretto project config
FDSNWS_URL = "http://bedretto-dev.ethz.ch:8080/fdsnws/event/1/query" \
    "?minmagnitude=-7"
HYDWS_URL = "http://bedretto-hydws.ethz.ch:8080/hydws/v1/boreholes" \
    "/c21pOmNoLmV0aHouc2VkL2JoL1NUMQ==?level=hydraulic"

model_requests_path = join(dirpath, 'model_requests')

model_request_1 = 'model_request_induced_1.json'

model_response_path = join(dirpath, 'results')

resources_path = join(dirpath, 'resources')
inj_plan_path = join(
    resources_path, 'injection_plan_150L_20220623.json')
disabled_bedretto_model_config_path = join(
    resources_path, 'model_bedretto_disabled.json')
enabled_bedretto_model_config_path = join(
    resources_path, 'model_bedretto_enabled.json')
bedretto_project_config_path = join(
    resources_path, 'project_bedretto_22062022.json')
bedretto_forecast_config_path = join(
    resources_path, 'forecast_bedretto_22062022.json')
fdsn_catalog_path = join(
    resources_path, '2022-06-22_fdsn_catalog.xml')
hyd_path = join(
    resources_path, '2022-06-22_hydws.json')


def mocked_requests_post(*args, **kwargs):
    logger.debug(f"Input to mocked_requests_post: {args}")
    if 'v1/sfm/models/em1/run' in args[0]:
        model_response_to_post_induced_1_path = join(
            model_response_path, 'model_response_to_post_induced_1.json')
        with open(model_response_to_post_induced_1_path, "r") as f:
            model_response_to_post_induced_1_data = json.load(f)
        return MockResponse(model_response_to_post_induced_1_data, 200)
    else:
        logger.warning("haven't caught request")

    return MockResponse(None, 404)


def mocked_datasources_get(*args, **kwargs):
    if args[0] == FDSNWS_URL:
        with open(fdsn_catalog_path, "rb") as f:
            data = f.read()
        return MockResponse({}, 200, data)
    elif args[0] == HYDWS_URL:
        with open(hyd_path, "rb") as f:
            data = f.read()
        return MockResponse({}, 200, data)

    elif 'v1/sfm/models/em1/run/'\
            '1bcc9e3f-d9bd-4dd2-a626-735cbef419dd' in args[0]:
        model_request_induced_1_path = join(
            model_response_path, "model_response_induced_1.json")
        with open(model_request_induced_1_path, "r") as f:
            model_response_induced_1_data = json.load(f)
        return MockResponse(model_response_induced_1_data, 200)

    return MockResponse(None, 404)


class TestInducedCase:
    def test_ramsis_bedretto_setup(self, mocker, session):
        check_updated_model(session, enabled_bedretto_model_config_path,
                            disabled_bedretto_model_config_path)
        create_project(bedretto_project_config_path)

        projects = session.execute(
            select(Project)).scalars().all()
        assert len(projects) == 1

        create_forecastseries(bedretto_forecast_config_path, "1")
        forecastseries = session.execute(
            select(ForecastSeries)).scalars().all()
        assert len(forecastseries) == 1

    @pytest.mark.run(after='test_ramsis_bedretto_setup')
    def test_run_bedretto_forecast(self, mocker, session):
            from RAMSIS.cli import ramsis_app as app
            from RAMSIS.db import db_url
            from RAMSIS.flows.forecast import scheduled_ramsis_flow
            mock_get = mocker.patch('RAMSIS.core.datasources.requests.get')
            mock_get.side_effect = mocked_datasources_get
            mock_post = mocker.patch('RAMSIS.core.worker.sfm.requests.post')
            #mock_post.side_effect = mocked_requests_post
            #_ = mocker.patch('RAMSIS.cli.forecast.schedule_forecast')
            forecastseries = check_one_forecastseries_in_db(session)
            logger.debug(f"Forecast created in test_run_forecast: {forecastseries.id}")
            with prefect_test_harness():
                result = scheduled_ramsis_flow(forecastseries.id, db_url, forecastseries.starttime)
            #result = runner.invoke(app, ["forecastsseries", "schedule",
            #                             str(forecastseries.id)])
            #logger.info(f"result stdout from invoking forecast: {result.stdout}")
            #assert result.exit_code == 0

    #@pytest.mark.run(after='test_run_bedretto_forecast')
    #def test_run_bedretto_engine_flow(self, mocker):
    #    with session_handler(db_url) as session:
    #        mock_get = mocker.patch('RAMSIS.core.datasources.requests.get')
    #        mock_get.side_effect = mocked_datasources_get
    #        mock_post = mocker.patch('RAMSIS.core.worker.sfm.requests.post')
    #        mock_post.side_effect = mocked_requests_post
    #        forecast_id = "1"

    #        from RAMSIS.cli import ramsis_app as app

    #        forecast = check_one_forecast_in_db(session)
    #        result = runner.invoke(app, ["engine", "run",
    #                                     forecast_id])
    #        logger.debug("result stdout from running forecast engine: "
    #                     f"{result.stdout}")
    #        assert result.exit_code == 0

    #        forecast = get_forecast(session, forecast.id)
    #        seismicity_results = forecast.scenarios[0][EStage.SEISMICITY].runs[0].\
    #            result.subgeometries[0].samples
    #        logger.info(f"length of seismicity results: {len(seismicity_results)}")
    #        assert len(seismicity_results) > 0
