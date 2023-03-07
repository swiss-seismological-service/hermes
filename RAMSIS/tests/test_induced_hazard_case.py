# For giving traceback from typer results:
# traceback.print_exception(*result.exc_info)
from sqlalchemy import select
import pytest
from typer.testing import CliRunner
import json
import logging

from ramsis.datamodel import Forecast, Project, EStage
from os.path import dirname, abspath, join

from RAMSIS.tests.utils import \
    create_project, create_forecast, \
    MockResponse, check_one_forecast_in_db, \
    get_forecast, add_haz_model, add_seis_model
from RAMSIS.db import session_handler, db_url

logger = logging.getLogger(__name__)

runner = CliRunner(echo_stdin=True)
dirpath = dirname(abspath(__file__))

# URLs are same as in bedretto project config
FDSNWS_URL = "http://bedretto-dev.ethz.ch:8080/fdsnws/event/1/query?minmagnitude=-7" # noqa
HYDWS_URL = "http://bedretto-hydws.ethz.ch:8080/hydws/v1/boreholes" \
    "/c21pOmNoLmV0aHouc2VkL2JoL1NUMQ==?level=hydraulic" # noqa

model_requests_path = join(dirpath, 'model_requests')

model_request_1 = 'model_request_induced_1.json'

model_response_path = join(dirpath, 'results')

resources_path = join(dirpath, 'resources')
inj_plan_path = join(
    resources_path, 'injection_plan_150L_20220623.json')
seis_model_config_path = join(
    resources_path, 'model_seis.json')
haz_model_config_path = join(
    resources_path, 'model_haz.json')
bedretto_project_config_path = join(
    resources_path, 'project_bedretto_22062022.json')
bedretto_forecast_config_path = join(
    resources_path, 'forecast_bedretto_22062022_haz.json')
fdsn_catalog_path = join(
    resources_path, '2022-06-22_fdsn_catalog.xml')
hyd_path = join(
    resources_path, '2022-06-22_hydws.json')
gsimlogictree_path = join(
    resources_path, 'gmpe_logic_tree.xml')
sourcemodeltemplate_path = join(
    resources_path, "model_source_template.xml")


def mocked_requests_post(*args, **kwargs):
    logger.debug(f"Input to mocked_requests_post: {args}")
    if args[0] == 'http://ramsis-em1.ethz.ch:5007/v1/sfm/models/em1/run':
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

    elif args[0] == 'http://ramsis-em1.ethz.ch:5007/v1/sfm/models/em1/run/'\
            '1bcc9e3f-d9bd-4dd2-a626-735cbef419dd':
        model_request_induced_1_path = join(
            model_response_path, "model_response_induced_1.json")
        with open(model_request_induced_1_path, "r") as f:
            model_response_induced_1_data = json.load(f)
        return MockResponse(model_response_induced_1_data, 200)

    return MockResponse(None, 404)


#class TestInducedHazCase:
#    def test_ramsis_haz_setup(self, mocker):
#        with session_handler(db_url) as session:
#            sm_result = add_seis_model(seis_model_config_path,
#                                       sourcemodeltemplate_path)
#            assert sm_result.exit_code == 0
#            hm_result = add_haz_model(haz_model_config_path,
#                                      gsimlogictree_path)
#            assert hm_result.exit_code == 0
#            create_project(bedretto_project_config_path)
#
#            projects = session.execute(
#                select(Project)).scalars().all()
#            assert len(projects) == 1
#
#            _ = create_forecast(
#                bedretto_forecast_config_path, "1",
#                inj_plan=inj_plan_path)
#            forecasts = session.execute(
#                select(Forecast)).scalars().all()
#            assert len(forecasts) == 1
#
#    @pytest.mark.run(after='test_ramsis_bedretto_setup')
#    def test_run_haz_forecast(self, mocker):
#        with session_handler(db_url) as session:
#            label = "client_testing_agent"
#            idempotency_id = "test_idempotency_id_"
#
#            from RAMSIS.cli import ramsis_app as app
#            _ = mocker.patch('RAMSIS.cli.forecast.schedule_forecast')
#            forecast = check_one_forecast_in_db(session)
#            logger.debug("Forecast created in test_run_forecast: "
#                         f"{forecast.id}")
#            result = runner.invoke(app, ["forecast", "run",
#                                         str(forecast.id), "--force",
#                                         "--label", label,
#                                         "--idempotency-id", idempotency_id])
#            logger.info("result stdout from invoking forecast:"
#                        f" {result.stdout}")
#            assert result.exit_code == 0
#
#    @pytest.mark.run(after='test_run_bedretto_forecast')
#    def test_run_haz_engine_flow(self, mocker):
#        # adding the mocks seem to also mock requests in the ramsis-hazard
#        # mock_get = mocker.patch('RAMSIS.core.datasources.requests.get')
#        # mock_get.side_effect = mocked_datasources_get
#        # mock_post = mocker.patch('RAMSIS.core.worker.sfm.requests.post')
#        # mock_post.side_effect = mocked_requests_post
#        with session_handler(db_url) as session:
#            forecast_id = "1"
#
#            from RAMSIS.cli import ramsis_app as app
#
#            forecast = check_one_forecast_in_db(session)
#            result = runner.invoke(app, ["engine", "run",
#                                         forecast_id])
#            print(result.stdout)
#            logger.debug("result stdout from running forecast engine: "
#                         f"{result.stdout}")
#            assert result.exit_code == 0
#
#            forecast = get_forecast(session, forecast.id)
#            seismicity_results = forecast.scenarios[0][EStage.SEISMICITY].\
#                runs[0].result.subgeometries[0].samples
#            logger.info("length of seismicity results: "
#                        f"{len(seismicity_results)}")
#            assert len(seismicity_results) > 0
