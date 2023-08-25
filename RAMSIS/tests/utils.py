"""
Testing utilities for setting up a ramsis forecast ready to run.
"""
from typer.testing import CliRunner
from sqlalchemy import select

from os.path import dirname, abspath

from ramsis.datamodel import ModelConfig, ForecastSeries

runner = CliRunner()
dirpath = dirname(abspath(__file__))


def check_one_model_in_db(session):
    models = session.execute(
        select(ModelConfig)).scalars().all()
    assert len(models) == 1
    return models[0]


def load_model(model_config):
    from RAMSIS.cli import ramsis_app as app
    options = ["model", "load",
               "--model-config",
               model_config]
    result = runner.invoke(app, options)
    print("result", result.stdout)
    return result


def check_updated_model(session, enabled_model_config, disabled_model_config):
    result = load_model(disabled_model_config)
    assert result.exit_code == 0

    existing_model = check_one_model_in_db(session)
    assert existing_model.enabled is False

    # test update of model.
    result2 = load_model(enabled_model_config)
    print("result", result.stdout)
    assert result2.exit_code == 0
    session.refresh(existing_model)
    assert existing_model.enabled is True


def create_project(project_config, catalog_data=None, well_data=None):
    from RAMSIS.cli import ramsis_app as app
    options = ["project", "create",
               "--config",
               project_config]
    if catalog_data:
        options.extend(["--catalog-data", catalog_data])
    if well_data:
        options.extend(["--well-data", well_data])
    result = runner.invoke(app, options)
    print("result", result.stdout)
    assert result.exit_code == 0


def create_forecastseries(forecastseries_config, project_id):
    from RAMSIS.cli import ramsis_app as app
    options = ["forecastseries", "create",
               "--project-id", project_id,
               "--config",
               forecastseries_config]
    result = runner.invoke(app, options)
    print("result", result.stdout)
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


def check_one_forecastseries_in_db(session):
    forecastseries = session.execute(
        select(ForecastSeries)).scalars().all()
    if not forecastseries:
        raise Exception("no forecastseries exists!")
    return forecastseries[0]


def get_forecastseries(session, forecastseries_id):
    forecastseries = session.execute(
        select(ForecastSeries).filter_by(id=forecastseries_id)).\
        scalar_one_or_none()
    return forecastseries
