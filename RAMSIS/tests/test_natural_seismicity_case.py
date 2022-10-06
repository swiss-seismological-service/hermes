from sqlalchemy import select
import pytest
from typer.testing import CliRunner
import json
import logging

from os.path import dirname, abspath, join
from RAMSIS.tests.utils import update_model, \
    create_project, create_forecast, \
    MockResponse, check_one_forecast_in_db, \
    get_forecast
from ramsis.datamodel import Forecast, Project, EStage

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

datasources_path = join(dirpath, 'datasources')

catalog_name = "1992-2021_fdsn_catalog_etas_switz.xml"

model_requests_path = join(dirpath, 'model_requests')

model_request_1 = 'model_request_induced_1.json'

model_response_path = join(dirpath, 'results')


def mocked_requests_post(*args, **kwargs):
    logger.debug(f"Input to mocked_requests_post: {args}")
    if args[0] == 'http://ramsis-em1.ethz.ch:5007/v1/sfm/models/etas/run':
        model_response_to_post_induced_1_path = join(
            model_response_path, 'model_response_to_post_induced_1.json')
        with open(model_response_to_post_induced_1_path, "r") as f:
            model_response_to_post_induced_1_data = json.load(f)
        return MockResponse(model_response_to_post_induced_1_data, 200)
    else:
        logger.warning("haven't caught request")

    return MockResponse(None, 404)


def mocked_datasources_get(*args, **kwargs):
    if FDSNWS_URL in args[0]:
        fdsn_catalog_path = join(
            datasources_path, catalog_name)
        with open(fdsn_catalog_path, "rb") as f:
            data = f.read()
        return MockResponse({}, 200, data)

    elif args[0] == 'http://ramsis-em1.ethz.ch:5007/v1/sfm/models/etas/run/'\
            '1bcc9e3f-d9bd-4dd2-a626-735cbef419dd':
        # TODO Replace these induced results with natural seismicity results
        # As soon as we have some results from here.
        model_request_induced_1_path = join(
            model_response_path, "model_response_induced_1.json")
        with open(model_request_induced_1_path, "r") as f:
            model_response_induced_1_data = json.load(f)
        return MockResponse(model_response_induced_1_data, 200)

    return MockResponse(None, 404)


class TestNaturalCase:
    @pytest.mark.run(after='test_run_bedretto_forecast')
    def test_ramsis_etas_setup(self):
        update_model(etas_model_config_path)
        create_project(etas_project_config_path)
        from RAMSIS.db import store
        session = store.session
        projects = session.execute(
            select(Project)).scalars().all()
        assert len(projects) == 1
        create_forecast(etas_forecast_config_path, "1",
                        catalog_data=etas_catalog_data_path)
        session = store.session
        forecasts = session.execute(
            select(Forecast)).scalars().all()
        assert len(forecasts) == 1

    @pytest.mark.run(after='test_ramsis_etas_setup')
    def test_etas_run_forecast(self, mocker):
        _ = mocker.patch('RAMSIS.cli.forecast.restart_flow_run')
        label = "client_testing_agent"
        idempotency_id = "test_idempotency_id_"
        from RAMSIS.db import store
        from RAMSIS.cli import ramsis_app as app
        session = store.session
        forecast = check_one_forecast_in_db(session)
        logger.debug(f"Forecast created in test_run_forecast: {forecast.id}")
        result = runner.invoke(app, ["forecast", "run",
                                     str(forecast.id), "--force",
                                     "--label", label,
                                     "--idempotency-id", idempotency_id])
        logger.debug(f"result stdout from invoking forecast: {result.stdout}")
        assert result.exit_code == 0

    @pytest.mark.run(after='test_etas_run_forecast')
    def test_etas_run_engine_flow(self, mocker):
        mock_get = mocker.patch('RAMSIS.core.datasources.requests.get')
        mock_get.side_effect = mocked_datasources_get
        mock_post = mocker.patch('RAMSIS.core.worker.sfm.requests.post')
        mock_post.side_effect = mocked_requests_post
        forecast_id = "1"
        from RAMSIS.db import store
        from RAMSIS.cli import ramsis_app as app
        session = store.session
        forecast = check_one_forecast_in_db(session)

        result = runner.invoke(app, ["engine", "run",
                                     forecast_id])
        logger.debug("result stdout from running forecast engine: "
                     f"{result.stdout}")
        assert result.exit_code == 0
        forecast = get_forecast(session, forecast.id)
        seismicity_results = forecast.scenarios[0][EStage.SEISMICITY].runs[0].\
            result.subgeometries[0].samples
        logger.info(f"length of seismicity results: {len(seismicity_results)}")
        assert len(seismicity_results) > 0
