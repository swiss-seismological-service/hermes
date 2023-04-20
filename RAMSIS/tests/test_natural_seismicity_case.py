# For giving traceback from typer results:
# traceback.print_exception(*result.exc_info)
from sqlalchemy import select
import pytest
from typer.testing import CliRunner
import json
import logging
from prefect.testing.utilities import prefect_test_harness

from ramsis.datamodel import ForecastSeries, Project
from os.path import dirname, abspath, join

from RAMSIS.tests.utils import check_updated_model, load_model, \
    create_project, create_forecastseries, \
    MockResponse, check_one_forecastseries_in_db, \
    get_forecastseries

logger = logging.getLogger(__name__)

runner = CliRunner(echo_stdin=True)
dirpath = dirname(abspath(__file__))
resources_path = join(dirpath, 'resources')
etas_model_config_path = join(
    resources_path, 'model_etas.json')
etas_project_config_path = join(
    resources_path, 'project_etas.json')
etas_forecast_config_path = join(
    resources_path, 'forecast_etas.json')
etas_catalog_data_path = join(
    resources_path, '1992-2021_fdsn_catalog_etas_switz.xml')


FDSNWS_URL = "http://arclink.ethz.ch/fdsnws/event/1/query?minmagnitude=-0.04"

model_requests_path = join(dirpath, 'model_requests')

model_response_path = join(dirpath, 'results')


def mocked_requests_post_etas(*args, **kwargs):
    logger.debug(f"Input to mocked_requests_post: {args}")
    if 'v1/sfm/run' in args[0]:
        model_response_to_post_path = join(
            model_response_path, 'model_response_to_post_natural_1.json')
        with open(model_response_to_post_path, "r") as f:
            model_response_to_post_data = json.load(f)
        return MockResponse(model_response_to_post_data, 200)
    else:
        logger.warning("haven't caught request")

    return MockResponse(None, 404)


def mocked_datasources_get_etas(*args, **kwargs):
    if args[0] == FDSNWS_URL:
        with open(etas_catalog_data_path, "rb") as f:
            data = f.read()
        return MockResponse({}, 200, data)

    elif 'v1/sfm/run/'\
            '1bcc9e3f-d9bd-4dd2-a626-735cbef419dd' in args[0]:
        model_request_response_path = join(
            model_response_path, "model_response_natural.json")
        with open(model_request_response_path, "r") as f:
            model_response_data = json.load(f)
        retval = MockResponse(model_response_data, 200)
        return retval

    return MockResponse(None, 404)


class TestInducedCase:
    @pytest.mark.run(after='test_run_bedretto_forecast')
    def test_ramsis_etas_setup(self, mocker, session):
        load_model(etas_model_config_path)
        create_project(etas_project_config_path)

        projects = session.execute(
            select(Project)).scalars().all()
        assert len(projects) == 1

        create_forecastseries(etas_forecast_config_path, "1")
        forecastseries = session.execute(
            select(ForecastSeries)).scalars().all()
        assert len(forecastseries) == 1


    @pytest.mark.run(after='test_ramsis_etas_setup')
    def test_run_etas_forecast(self, mocker, session):
        from RAMSIS.cli import ramsis_app as app
        from RAMSIS.db import db_url
        from RAMSIS.flows.forecast import scheduled_ramsis_flow
        mock_get = mocker.patch('RAMSIS.core.datasources.requests.get')
        mock_get.side_effect = mocked_datasources_get_etas
        forecastseries = check_one_forecastseries_in_db(session)
        logger.debug(f"Forecastseries created in test_run_forecast: {forecastseries.id}")
        with prefect_test_harness():
            result = scheduled_ramsis_flow(forecastseries.id, db_url, forecastseries.starttime)
