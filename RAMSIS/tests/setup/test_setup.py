# For giving traceback from typer results:
# traceback.print_exception(*result.exc_info)
from sqlalchemy import select
from typer.testing import CliRunner
import logging

from ramsis.datamodel import ForecastSeries, Project, ModelConfig
from os.path import dirname, abspath, join

from RAMSIS.tests.utils import load_model, \
    create_project, create_forecastseries

logger = logging.getLogger(__name__)

runner = CliRunner(echo_stdin=True)
dirpath = join(dirname(abspath(__file__)), '..')

model_requests_path = join(dirpath, 'model_requests')

model_request_1 = 'model_request_induced_1.json'

model_response_path = join(dirpath, 'results')

res = join(dirpath, 'resources')
hyd_path = '2022-04-21_hydws.json'
inj_plan_path = '16A-32_forge_2022_04_21_plan.json'
cat_path = '2022-04-21_fdsn_catalog.xml'
model_config_path = 'model_forge_2022.json'
project_config_path = 'project_forge_2022.json'
forecast_config_path = 'forecast_forge_2022.json'


def test_multi_setup(
        mocker, session):
    model_config_path, project_config_path, \
        forecast_config_path, cat_path, hyd_path = (
            'model_forge_2022.json', 'project_forge_2022.json',
            'forecast_forge_2022.json',
            '2022-04-21_fdsn_catalog.xml', '2022-04-21_hydws.json')
    _ = load_model(join(res, model_config_path))
    models = session.execute(
        select(ModelConfig)).scalars().all()
    assert len(models) == 1
    create_project(join(res, project_config_path),
                   well_data=join(res, hyd_path),
                   catalog_data=join(res, cat_path))
    projects = session.execute(
        select(Project)).scalars().all()
    assert len(projects) == 1

    create_forecastseries(join(res, forecast_config_path), "1")
    forecastseries = session.execute(
        select(ForecastSeries)).scalars().all()
    assert len(forecastseries) == 1
