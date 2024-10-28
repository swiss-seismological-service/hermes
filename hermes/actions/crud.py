from uuid import UUID

from sqlalchemy.exc import IntegrityError

from hermes.repositories.database import Session
from hermes.repositories.project import (ForecastSeriesRepository,
                                         ModelConfigRepository,
                                         ProjectRepository)
from hermes.repositories.results import ModelRunRepository
from hermes.schemas import EStatus, ForecastSeriesConfig, ModelConfig


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


def read_modelconfig_oid(name_or_id: str):
    try:
        return UUID(name_or_id, version=4)
    except ValueError:
        with Session() as session:
            model_config_db = ModelConfigRepository.get_by_name(
                session, name_or_id)

        if not model_config_db:
            raise Exception(f'ModelConfig "{name_or_id}" not found.')

        return model_config_db.oid


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
                          force: bool = False):

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
                    'Use --force to update anyway.')

    new_data = ForecastSeriesConfig(oid=forecastseries_oid,
                                    **fseries_config)

    with Session() as session:
        forecast_series_out = ForecastSeriesRepository.update(
            session, new_data)

    return forecast_series_out


def update_modelconfig(new_config: dict,
                       modelconfig_oid: UUID,
                       force: bool = False):

    if not force:
        with Session() as session:
            modelruns = ModelRunRepository.get_by_modelconfig(
                session, modelconfig_oid)
        if len(modelruns) > 0:
            raise Exception(
                'ModelConfig cannot be updated because it is associated with '
                'one or more ModelRuns. Use --force to update anyway.')

    new_data = ModelConfig(oid=modelconfig_oid, **new_config)

    with Session() as session:
        model_config_out = ModelConfigRepository.update(session, new_data)

    return model_config_out


def delete_modelconfig(modelconfig_oid: UUID):
    with Session() as session:
        modelruns = ModelRunRepository.get_by_modelconfig(
            session, modelconfig_oid)
    if len(modelruns) > 0:
        raise Exception(
            'ModelConfig cannot be deleted because it is associated with '
            'one or more ModelRuns. Delete the ModelRuns first.')

    with Session() as session:
        ModelConfigRepository.delete(session, modelconfig_oid)


def enable_modelconfig(modelconfig_oid: UUID):
    with Session() as session:
        model_config = ModelConfigRepository.get_by_id(
            session, modelconfig_oid)
        model_config.enabled = True
        return ModelConfigRepository.update(session, model_config)


def disable_modelconfig(modelconfig_oid: UUID):
    with Session() as session:
        model_config = ModelConfigRepository.get_by_id(
            session, modelconfig_oid)
        model_config.enabled = False
        return ModelConfigRepository.update(session, model_config)


def archive_modelconfig(modelconfig_oid: UUID):
    with Session() as session:
        model_config = ModelConfigRepository.get_by_id(
            session, modelconfig_oid)
        model_config.enabled = False
        base_name = model_config.name

    try:
        with Session() as session:
            model_config.name = f'{base_name}_archived'
            model_config = ModelConfigRepository.update(session, model_config)
            return model_config
    except IntegrityError:
        for i in range(1, 100):
            with Session() as session:
                try:
                    model_config.name = f'{base_name}_archived_{i}'
                    model_config = ModelConfigRepository.update(
                        session, model_config)
                    return model_config
                except IntegrityError:
                    continue


def create_modelconfig(name, model_config):
    model_config = ModelConfig(name=name, **model_config)
    try:
        with Session() as session:
            model_config_out = ModelConfigRepository.create(
                session, model_config)
        return model_config_out
    except IntegrityError:
        raise ValueError(f'ModelConfig with name "{name}" already exists,'
                         ' please choose a different name or archive the'
                         ' existing ModelConfig with the same name.')
    except Exception as e:
        raise e
