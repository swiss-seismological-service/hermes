"""
Testing utilities for setting up a ramsis forecast ready to run.
"""
from typer.testing import CliRunner
from sqlalchemy import select

from os.path import dirname, abspath

from ramsis.datamodel import SeismicityModel, Forecast

runner = CliRunner()
dirpath = dirname(abspath(__file__))


def check_one_model_in_db(session):
    models = session.execute(
        select(SeismicityModel)).scalars().all()
    assert len(models) == 1
    return models[0]


def update_model(model_config):
    from RAMSIS.cli import ramsis_app as app
    result = runner.invoke(app, ["model", "configure",
                                 "--model-config",
                                 model_config])
    return result


def check_updated_model(enabled_model_config, disabled_model_config):
    # import these after environment is set to test mode
    from RAMSIS.db import store
    result = update_model(disabled_model_config)
    assert result.exit_code == 0

    session = store.session
    disabled_model = check_one_model_in_db(session)
    assert disabled_model.enabled is False

    # test update of model.
    update_model(enabled_model_config)
    assert result.exit_code == 0
    enabled_model = check_one_model_in_db(session)
    assert enabled_model.enabled is True
    store.close()


def create_project(project_config):
    from RAMSIS.cli import ramsis_app as app
    result = runner.invoke(app, ["project", "create",
                                 "--config",
                                 project_config])
    assert result.exit_code == 0


def create_forecast(forecast_config, project_id, inj_plan=None,
                    catalog_data=None):
    from RAMSIS.cli import ramsis_app as app
    options = ["forecast", "create",
               "--project-id", project_id,
               "--config",
               forecast_config]
    if inj_plan:
        options.extend([
            "--inj-plan-data",
            inj_plan])
    if catalog_data:
        options.extend([
            "--catalog-data",
            catalog_data])
    result = runner.invoke(app, options)
    assert result.exit_code == 0


class MockResponse:
    def __init__(self, json_data, status_code, content=None):
        self.json_data = json_data
        self.status_code = status_code
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return self.json_data

    def url(self):
        return "Some url"


def check_one_forecast_in_db(session):
    forecasts = session.execute(
        select(Forecast)).scalars().all()
    if not forecasts:
        raise Exception("no forecast exists!")
    return forecasts[0]


def get_forecast(session, forecast_id):
    forecast = session.execute(
        select(Forecast).filter_by(id=forecast_id)).scalar_one_or_none()
    return forecast
