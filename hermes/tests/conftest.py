from datetime import datetime

import pytest
from shapely import Polygon

from config import get_settings
from hermes.repositories.project import (ForecastSeriesRepository,
                                         ModelConfigRepository,
                                         ProjectRepository)
from hermes.repositories.tests.conftest import connection, session, setup_db
from hermes.schemas import (EInput, EResultType, EStatus, ForecastSeries,
                            ModelConfig, Project)

settings = get_settings()

# session fixture
session

# connection fixture
connection

# setup_db fixture
setup_db


@pytest.fixture()
def project(session) -> Project:
    project = Project(
        name='test_project',
        description='test_description',
        starttime=datetime(2024, 1, 1, 0, 0, 0),
        endtime=datetime(2024, 2, 1, 0, 0, 0),
        seismicityobservation_required=EInput.REQUIRED,
        injectionobservation_required=EInput.NOT_ALLOWED,
        injectionplan_required=EInput.NOT_ALLOWED,
        fdsnws_url='https://'
    )

    project = ProjectRepository.create(session, project)

    return project


@pytest.fixture()
def forecastseries(session, project):
    forecastseries = ForecastSeries(
        name='test_forecastseries',
        forecast_starttime=datetime(2021, 1, 2, 0, 0, 0),
        forecast_endtime=datetime(2021, 1, 4, 0, 0, 0),
        observation_starttime=datetime(2021, 1, 1, 0, 0, 0),
        project_oid=project.oid,
        status=EStatus.PENDING,
        forecast_interval=1800,
        bounding_polygon=Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]),
        depth_min=0,
        depth_max=1,
        tags=['tag1', 'tag2']
    )

    forecastseries = ForecastSeriesRepository.create(session, forecastseries)

    return forecastseries


@pytest.fixture()
def model_config(session):
    model_config = ModelConfig(
        name='test_model',
        description='test_description',
        tags=['tag1', 'tag3'],
        result_type=EResultType.CATALOG,
        enabled=True,
        sfm_module='test_module',
        sfm_function='test_function',
        model_parameters={'setting1': 'value1',
                          'setting2': 'value2'}
    )
    model_config = ModelConfigRepository.create(session, model_config)
    return model_config
