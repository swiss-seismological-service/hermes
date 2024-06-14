# For giving traceback from typer results:
# traceback.print_exception(*result.exc_info)
import json
import logging
from datetime import datetime
from os.path import abspath, dirname, join

from ramsis.datamodel import (Forecast, ForecastSeries, ModelConfig, ModelRun,
                              Project)
from sqlalchemy import select
from typer.testing import CliRunner

from hermes.tests.utils import (create_forecastseries, create_project,
                                delete_model, load_model)

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


def test_load_two_models(session, tmp_path):
    """ Test that loading two models results
    in two models added to the database.
    """

    # load default model config first
    _ = load_model(join(res, model_config_path))
    models = session.execute(
        select(ModelConfig)).scalars().all()
    assert len(models) == 1

    # save config with updated name, then load.
    renamed_config = join(tmp_path, "model_config_renamed.json")
    model_name = "Model Name"
    with open(join(res, model_config_path)) as o_file:
        json_config = json.load(o_file)
    json_config["model_configs"][0]["name"] = model_name
    with open(renamed_config, "w") as w_file:
        json.dump(json_config, w_file)

    _ = load_model(join(res, renamed_config))
    models = session.execute(
        select(ModelConfig)).scalars().all()
    assert len(models) == 2


def test_replace_model_config(session, tmp_path):
    """ Test that reloading a model config results
    in deletion and readding to the database.
    """

    # load default model config first
    _ = load_model(join(res, model_config_path))
    models = session.execute(
        select(ModelConfig)).scalars().all()
    assert len(models) == 1

    # save config with updated name, then load.
    renamed_config = join(tmp_path, "model_config_renamed.json")
    model_enabled = False
    model_tags = ["TAG1"]
    with open(join(res, model_config_path)) as o_file:
        json_config = json.load(o_file)
    json_config["model_configs"][0]["enabled"] = model_enabled
    json_config["model_configs"][0]["tags"] = model_tags
    with open(renamed_config, "w") as w_file:
        json.dump(json_config, w_file)

    _ = load_model(join(res, renamed_config))
    session.expire_all()
    models = session.execute(
        select(ModelConfig)).scalars().all()
    assert len(models) == 1
    assert models[0].enabled == model_enabled
    assert len(models[0].tags) == 1
    assert models[0].tags[0].name == model_tags[0]


def test_load_model_completed_forecasts(session, tmp_path):
    """ Test that loading the model for a second time
    fails after there are model runs associated with the
    model config.
    """

    # load default model config first
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
    models = session.execute(
        select(ModelConfig)).scalars().all()
    runs = [ModelRun(modelconfig=models[0])]
    forecastseries[0].forecasts = [
        Forecast(starttime=datetime(2023, 10, 10),
                 endtime=datetime(2023, 10, 11),
                 runs=runs)]
    session.commit()
    result = load_model(join(res, model_config_path))

    assert result.exit_code == 1
    session.expire_all()
    models = session.execute(
        select(ModelConfig)).scalars().all()
    assert len(models) == 1


def test_model_delete(session, tmp_path):
    _ = load_model(join(res, model_config_path))
    models = session.execute(
        select(ModelConfig)).scalars().all()
    assert len(models) == 1

    _ = delete_model("EM1-MLE Forge")
    session.expire_all()
    models = session.execute(
        select(ModelConfig)).scalars().all()
    assert len(models) == 0
