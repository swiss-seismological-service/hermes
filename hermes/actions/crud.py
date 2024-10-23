from uuid import UUID

from hermes.repositories.database import Session
from hermes.repositories.project import (ForecastSeriesRepository,
                                         ProjectRepository)
from hermes.schemas import EStatus
from hermes.schemas.project_schemas import ForecastSeriesConfig


def read_forecastseries_oid(name_or_id: str):
    try:
        return UUID(name_or_id, version=4)
    except ValueError:
        with Session() as session:
            forecastseries_db = ForecastSeriesRepository.get_by_name(
                session, name_or_id)

        if not forecastseries_db:
            raise Exception(f'ForecastSeries "{name_or_id}" not found.')

        return forecastseries_db.oid


def read_project_oid(name_or_id: str):
    try:
        return UUID(name_or_id, version=4)
    except ValueError:
        with Session() as session:
            project_db = ProjectRepository.get_by_name(session, name_or_id)

        if not project_db:
            raise Exception(f'Project "{name_or_id}" not found.')

        return project_db.oid


def create_forecastseries(name, fseries_config, project_oid):
    forecast_series = ForecastSeriesConfig(name=name,
                                           status=EStatus.PENDING,
                                           project_oid=project_oid,
                                           **fseries_config)

    with Session() as session:
        forecast_series_out = ForecastSeriesRepository.create(
            session, forecast_series)

    return forecast_series_out


def update_forecastseries(fseries_config: dict,
                          forecastseries_oid: UUID,
                          force: bool):

    if not force:
        protected_fields = ['project_oid',
                            'status',
                            'observation_starttime',
                            'observation_endtime',
                            'bounding_polygon',
                            'depth_min',
                            'depth_max',
                            'seismicityobservation_required',
                            'injectionobservation_required',
                            'injectionplan_required']
        for field in protected_fields:
            if field in fseries_config.keys():
                raise Exception(
                    f'Field "{field}" should not be updated. '
                    'Use --force to update anywas.')

    new_data = ForecastSeriesConfig(oid=forecastseries_oid,
                                    **fseries_config)

    with Session() as session:
        forecast_series_out = ForecastSeriesRepository.update(
            session, new_data)

    return forecast_series_out
