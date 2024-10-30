import asyncio
from uuid import UUID

from hermes.flows.forecastseries_scheduler import (DEPLOYMENT_NAME,
                                                   ForecastSeriesScheduler,
                                                   delete_deployment_schedule)
from hermes.repositories.database import Session
from hermes.repositories.project import (ForecastRepository,
                                         ForecastSeriesRepository,
                                         ModelConfigRepository,
                                         ProjectRepository)
from hermes.repositories.results import ModelRunRepository
from hermes.repositories.types import DuplicateError
from hermes.schemas import EStatus, ForecastSeriesConfig, ModelConfig
from hermes.schemas.project_schemas import Project


def read_project_oid(name_or_id: str):
    try:
        return UUID(name_or_id, version=4)
    except ValueError:
        with Session() as session:
            project_db = ProjectRepository.get_by_name(session, name_or_id)

        if not project_db:
            raise Exception(f'Project "{name_or_id}" not found.')

        return project_db.oid


def update_project(new_config: dict,
                   project_oid: UUID):

    new_data = Project(oid=project_oid, **new_config)

    try:
        with Session() as session:
            project_out = ProjectRepository.update(session, new_data)
    except DuplicateError:
        raise ValueError(f'Project with name "{new_config["name"]}"'
                         ' already exists, please choose a different name.')

    return project_out


def delete_project(project_oid: UUID):
    # delete all forecastseries separately to ensure correct deletion
    # of associated forecasts and schedules
    with Session() as session:
        forecastseries = ForecastSeriesRepository.get_by_project(
            session, project_oid)

    for fseries in forecastseries:
        delete_forecastseries(fseries.oid)

    # delete project
    with Session() as session:
        ProjectRepository.delete(session, project_oid)


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


def create_forecastseries(name, fseries_config, project_oid):
    forecast_series = ForecastSeriesConfig(name=name,
                                           status=EStatus.PENDING,
                                           project_oid=project_oid,
                                           **fseries_config)
    try:
        with Session() as session:
            forecast_series_out = ForecastSeriesRepository.create(
                session, forecast_series)

        return forecast_series_out
    except DuplicateError:
        raise ValueError(f'ForecastSeries with name "{name}" already exists,'
                         ' please choose a different name.')


def update_forecastseries(fseries_config: dict,
                          forecastseries_oid: UUID,
                          force: bool = False):

    new_forecastseries = ForecastSeriesConfig(oid=forecastseries_oid,
                                              **fseries_config)

    # the following fields should generally not be updated,
    # check whether they are being updated and raise an exception
    # if not forced
    if not force:
        with Session() as session:
            old_forecastseries = ForecastSeriesRepository.get_by_id(
                session, forecastseries_oid)

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
                if getattr(old_forecastseries, field) != \
                        getattr(new_forecastseries, field):
                    raise Exception(
                        f'Field "{field}" should not be updated. '
                        'Use --force to update anyway.')

    try:
        with Session() as session:
            forecast_series_out = ForecastSeriesRepository.update(
                session, new_forecastseries)
    except DuplicateError:
        raise ValueError(f'ForecastSeries with name "{fseries_config["name"]}"'
                         ' already exists, please choose a different name.')

    return forecast_series_out


def delete_forecastseries(forecastseries_oid: UUID):

    # check no forecasts are running
    with Session() as session:
        forecasts = ForecastRepository.get_by_forecastseries(
            session, forecastseries_oid)
    if any(f.status == EStatus.RUNNING for f in forecasts):
        raise Exception(
            'ForecastSeries cannot be deleted because it is currently running.'
            ' Stop the forecasts first.')

    # delete schedule if exists
    with Session() as session:
        forecastseries = ForecastSeriesRepository.get_by_id(
            session, forecastseries_oid)
    if forecastseries.schedule_id:
        asyncio.run(delete_deployment_schedule(
            DEPLOYMENT_NAME, forecastseries.schedule_id))

    # delete forecastseries
    with Session() as session:
        ForecastSeriesRepository.delete(session, forecastseries_oid)


def create_modelconfig(name, model_config):
    model_config = ModelConfig(name=name, **model_config)
    try:
        with Session() as session:
            model_config_out = ModelConfigRepository.create(
                session, model_config)
        return model_config_out
    except DuplicateError:
        raise ValueError(f'ModelConfig with name "{name}" already exists,'
                         ' please choose a different name or archive the'
                         ' existing ModelConfig with the same name.')


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

    try:
        with Session() as session:
            model_config_out = ModelConfigRepository.update(session, new_data)
    except DuplicateError:
        raise ValueError(f'ModelConfig with name "{new_config["name"]}"'
                         ' already exists, please choose a different name.')

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
    except DuplicateError:
        for i in range(1, 100):
            with Session() as session:
                try:
                    model_config.name = f'{base_name}_archived_{i}'
                    model_config = ModelConfigRepository.update(
                        session, model_config)
                    return model_config
                except DuplicateError:
                    continue


def create_schedule(forecastseries_oid: UUID, schedule_config: dict):
    scheduler = ForecastSeriesScheduler(forecastseries_oid)

    if 'schedule_id' in schedule_config.keys():
        raise ValueError(
            'Schedule ID can not be set manually.'
        )

    scheduler.create_prefect_schedule(schedule_config)


def update_schedule(forecastseries_oid: UUID, schedule_config: dict):
    scheduler = ForecastSeriesScheduler(forecastseries_oid)

    if 'schedule_id' in schedule_config.keys():
        raise ValueError(
            'Schedule ID can not be set manually.'
        )

    scheduler.update_prefect_schedule(schedule_config)
