"""
Testing utilities for setting up a ramsis forecast ready to run.
"""


import pytest
from typer.testing import CliRunner
from sqlalchemy import select

from os.path import dirname, abspath, join

from ramsis.datamodel import SeismicityModel, Project, Forecast

runner = CliRunner()
dirpath = dirname(abspath(__file__))
config_path = join(dirpath, 'config')
inj_plan_path = join(
    config_path, 'injection_plan_150L_20220623.json')
disabled_model_config_path = join(
    config_path, 'model_bedretto_22062022_disabled.json')
enabled_model_config_path = join(
    config_path, 'model_bedretto_22062022_enabled.json')
project_config_path = join(config_path, 'project_bedretto_22062022.json')
forecast_config_path = join(config_path, 'forecast_bedretto_22062022.json')


def check_one_model_in_db(session):
    models = session.execute(
        select(SeismicityModel)).scalars().all()
    assert len(models) == 1
    return models[0]


def update_model():
    # import these after environment is set to test mode
    from RAMSIS.db import store
    from RAMSIS.cli import ramsis_app as app
    result = runner.invoke(app, ["model", "configure",
                                 "--model-config",
                                 disabled_model_config_path])
    assert result.exit_code == 0

    session = store.session
    disabled_model = check_one_model_in_db(session)
    assert disabled_model.enabled is False

    # test update of model.
    result = runner.invoke(app, ["model", "configure",
                                 "--model-config",
                                 enabled_model_config_path])
    assert result.exit_code == 0
    enabled_model = check_one_model_in_db(session)
    assert enabled_model.enabled is True
    store.close()


def create_project():
    from RAMSIS.db import store
    from RAMSIS.cli import ramsis_app as app
    session = store.session
    projects = session.execute(
        select(Project)).scalars().all()
    assert len(projects) == 0
    result = runner.invoke(app, ["project", "create",
                                 "--config",
                                 project_config_path])
    assert result.exit_code == 0
    session = store.session

    projects = session.execute(
        select(Project)).scalars().all()
    assert len(projects) == 1


def create_forecast():
    from RAMSIS.db import store, env
    from RAMSIS.cli import ramsis_app as app
    print('env in test', env)
    result = runner.invoke(app, ["forecast", "create",
                                 "--project-id", "1",
                                 "--inj-plan-data",
                                 inj_plan_path,
                                 "--config",
                                 forecast_config_path])
    print("result: ", result.stdout)
    assert result.exit_code == 0
    session = store.session

    forecasts = session.execute(
        select(Forecast)).scalars().all()
    assert len(forecasts) == 1
    print("forecast created in setup", forecasts)


@pytest.mark.order(1)
def test_ramsis_setup():
    update_model()
    create_project()
    create_forecast()
