import os
from datetime import datetime, timedelta

import numpy as np
from shapely.geometry import Polygon

from hermes.repositories.database import Session
from hermes.repositories.project import (ForecastSeriesRepository,
                                         ModelConfigRepository,
                                         ProjectRepository)
from hermes.schemas import (EInput, EResultType, EStatus, ForecastSeries,
                            Project)
from hermes.schemas.model_schemas import ModelConfig

MODULE_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)))


def project() -> Project:
    with Session() as session:
        project = Project(
            name='test_project',
            description='test_description',
            starttime=datetime.now() - timedelta(days=7),
            endtime=datetime.now() + timedelta(days=7),
        )

        project = ProjectRepository.create(session, project)

        forecastseries = ForecastSeries(
            name='test_forecastseries',
            schedule_starttime=datetime.now() + timedelta(hours=2),
            schedule_interval=30 * 60,
            schedule_endtime=datetime.now() + timedelta(hours=3),

            forecast_endtime=datetime.now() + timedelta(hours=4),
            forecast_duration=30 * 60,

            observation_starttime=datetime.now() - timedelta(days=365),

            project_oid=project.oid,
            status=EStatus.PENDING,
            bounding_polygon=Polygon(
                np.load(os.path.join(MODULE_LOCATION, 'ch_rect.npy'))),
            depth_min=0,
            depth_max=1,
            tags=['tag1', 'tag2'],
            seismicityobservation_required=EInput.REQUIRED,
            injectionobservation_required=EInput.NOT_ALLOWED,
            injectionplan_required=EInput.NOT_ALLOWED,
            fdsnws_url='http://eida.ethz.ch/fdsnws/event/1/query'
        )

        forecastseries = ForecastSeriesRepository.create(
            session, forecastseries)

        model_config = ModelConfig(
            name='test_model',
            description='test_description',
            tags=['tag1', 'tag3'],
            result_type=EResultType.CATALOG,
            enabled=True,
            sfm_module='etas.oef',
            sfm_function='entrypoint_suiETAS',
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
                "mc": 2.2,
                "m_ref": 2.2,
                "delta_m": 0.1,
                "coppersmith_multiplier": 100,
                "earth_radius": 6.3781e3,
                "auxiliary_start": "1992-01-01T00:00:00",
                "timewindow_start": "1997-01-01T00:00:00",
                "m_thr": 2.5,
                "n_simulations": 100
            })
        model_config = ModelConfigRepository.create(session, model_config)


if __name__ == '__main__':
    project()
