import os
import uuid
from datetime import datetime, timedelta

import numpy as np
import pytest
from prefect.logging import disable_run_logger
from prefect.testing.utilities import prefect_test_harness
from shapely import Polygon

from hermes.schemas import (DBModelRunInfo, EInput, EResultType, EStatus,
                            Forecast, ForecastSeries, ModelConfig, Project,
                            SeismicityObservation)

MODULE_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data')


@pytest.fixture(scope="class")
def prefect():
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
        endtime=datetime(2024, 2, 1, 0, 0, 0)
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
        tags=['tag1'],
        seismicityobservation_required=EInput.REQUIRED,
        injectionobservation_required=EInput.NOT_ALLOWED,
        injectionplan_required=EInput.NOT_ALLOWED,
        fdsnws_url='https://'
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
        model_parameters={'setting1': 'value1',
                          'setting2': 'value2'}
    )

    return model_config


@pytest.fixture()
def modelrun_info():
    return DBModelRunInfo(
        forecast_start=datetime(2022, 1, 1),
        forecast_end=datetime(2022, 1, 1) + timedelta(days=30),
        bounding_polygon=Polygon(
            np.load(os.path.join(MODULE_LOCATION, 'ch_rect.npy'))),
        depth_min=0,
        depth_max=1)


@pytest.fixture()
def modelconfig():
    return ModelConfig(
        oid=uuid.uuid4(),
        name='test',
        result_type=EResultType.CATALOG,
        sfm_module='hermes.flows.tests.test_model_runner',
        sfm_function='mock_function',
        model_parameters={
            "theta_0": {
                "log10_mu": -6.21,
                "log10_k0": -2.75,
                "a": 1.13,
                "log10_c": -2.85,
                "omega": -0.13,
                "log10_tau": 3.57,
                "log10_d": -0.51,
                "gamma": 0.15,
                "rho": 0.63
            },
            "mc": 2.3,
            "delta_m": 0.1,
            "coppersmith_multiplier": 100,
            "earth_radius": 6.3781e3,
            "auxiliary_start": datetime(1992, 1, 1),
            "timewindow_start": datetime(1997, 1, 1),
            "n_simulations": 100
        }
    )


@pytest.fixture()
def seismicity_observation():
    with open(os.path.join(MODULE_LOCATION, 'catalog.xml')) as f:
        catalog = f.read()
    return SeismicityObservation(data=catalog)
