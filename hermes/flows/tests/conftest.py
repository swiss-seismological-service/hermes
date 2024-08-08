import uuid
from datetime import datetime

import pytest
from prefect.logging import disable_run_logger
from prefect.testing.utilities import prefect_test_harness
from shapely import Polygon

from hermes.schemas import (EInput, EResultType, EStatus, Forecast,
                            ForecastSeries, ModelConfig, Project)


@pytest.fixture(autouse=True, scope="class")
def prefect_test_fixture():
    with prefect_test_harness():
        with disable_run_logger():
            yield


@pytest.fixture()
def project():
    project = Project(
        name='test_project',
        oid=uuid.uuid4(),
        description='test_description',
        starttime=datetime(2024, 1, 1, 0, 0, 0),
        endtime=datetime(2024, 2, 1, 0, 0, 0),
        seismicityobservation_required=EInput.REQUIRED,
        injectionobservation_required=EInput.NOT_ALLOWED,
        injectionplan_required=EInput.NOT_ALLOWED,
        fdsnws_url='https://'
    )
    return project


@pytest.fixture()
def forecastseries(project):
    forecastseries = ForecastSeries(
        name='test_forecastseries',
        oid=uuid.uuid4(),
        forecast_starttime=datetime(2021, 1, 2, 0, 0, 0),
        forecast_endtime=datetime(2021, 1, 4, 0, 0, 0),
        forecast_duration=1800,
        forecast_interval=1800,
        observation_starttime=datetime(2021, 1, 1, 0, 0, 0),
        project_oid=project.oid,
        status=EStatus.PENDING,
        bounding_polygon=Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]),
        depth_min=0,
        depth_max=1,
        tags=['tag1']
    )

    return forecastseries


@pytest.fixture()
def forecast(forecastseries):
    forecast = Forecast(
        name='test_forecast',
        oid=uuid.uuid4(),
        forecastseries_oid=forecastseries.oid,
        status=EStatus.PENDING,
        starttime=datetime(2021, 1, 2, 0, 30, 0),
        endtime=datetime(2021, 1, 4, 0, 0, 0),
    )
    return forecast


@pytest.fixture()
def model_config():
    model_config = ModelConfig(
        name='test_model',
        oid=uuid.uuid4(),
        description='test_description',
        tags=['tag1'],
        result_type=EResultType.CATALOG,
        enabled=True,
        sfm_module='test_module',
        sfm_function='test_function',
        config={'setting1': 'value1',
                'setting2': 'value2'}
    )

    return model_config
