from datetime import datetime

from shapely.geometry import Polygon

from hermes.repositories.database import Session
from hermes.repositories.project import (ForecastRepository,
                                         ForecastSeriesRepository,
                                         ModelConfigRepository,
                                         ProjectRepository)
from hermes.schemas import (EInput, EResultType, EStatus, Forecast,
                            ForecastSeries, Project)
from hermes.schemas.model_schemas import ModelConfig


def project() -> Project:
    with Session() as session:
        project = Project(
            name='test_project',
            description='test_description',
            starttime=datetime(2024, 1, 1, 0, 0, 0),
            endtime=datetime(2024, 2, 1, 0, 0, 0)
        )

        project = ProjectRepository.create(session, project)

        forecastseries = ForecastSeries(
            name='test_forecastseries',
            forecast_starttime=datetime(2021, 1, 2, 0, 0, 0),
            forecast_endtime=datetime(2021, 1, 4, 0, 0, 0),
            forecast_duration=3600,
            forecast_interval=1800,
            observation_starttime=datetime(2021, 1, 1, 0, 0, 0),
            project_oid=project.oid,
            status=EStatus.PENDING,
            bounding_polygon=Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]),
            depth_min=0,
            depth_max=1,
            tags=['tag1', 'tag2'],
            seismicityobservation_required=EInput.REQUIRED,
            injectionobservation_required=EInput.NOT_ALLOWED,
            injectionplan_required=EInput.NOT_ALLOWED,
            fdsnws_url='https://earthquake.usgs.gov/fdsnws/event/1/query',
        )

        forecastseries = ForecastSeriesRepository.create(
            session, forecastseries)

        forecast = Forecast(
            name='test_forecast',
            forecastseries_oid=forecastseries.oid,
            status=EStatus.PENDING,
            starttime=datetime(2021, 1, 2, 0, 30, 0),
            endtime=datetime(2021, 1, 4, 0, 0, 0),
        )

        forecast = ForecastRepository.create(session, forecast)

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


if __name__ == '__main__':
    project()
