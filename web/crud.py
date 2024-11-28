from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from hermes.datamodel import ProjectTable
from hermes.datamodel.data_tables import (InjectionObservationTable,
                                          InjectionPlanTable,
                                          SeismicityObservationTable)
from hermes.datamodel.project_tables import (ForecastSeriesTable,
                                             ForecastTable, ModelConfigTable,
                                             TagTable)
from hermes.datamodel.result_tables import ModelResultTable, ModelRunTable


async def read_all_projects(db: AsyncSession,
                            starttime: datetime | None = None) \
        -> list[ProjectTable]:

    statement = select(ProjectTable)

    if starttime:
        statement = statement.filter(ProjectTable.starttime > starttime)

    results = await db.execute(statement)

    return results.scalars().unique().all()


async def read_project(db: AsyncSession,
                       project_oid: UUID) -> \
        ProjectTable | None:

    statement = select(ProjectTable).where(ProjectTable.oid == project_oid)

    result = await db.execute(statement)

    return result.scalars().unique().one_or_none()


async def read_all_forecastseries(db: AsyncSession,
                                  project_oid: UUID) \
        -> list[ForecastSeriesTable]:

    statement = select(ForecastSeriesTable) \
        .options(joinedload(ForecastSeriesTable._tags),
                 joinedload(ForecastSeriesTable.injectionplans)) \
        .where(project_oid == project_oid)

    results = await db.execute(statement)

    return results.scalars().unique().all()


async def read_forecastseries(db: AsyncSession,
                              forecastseries_oid: UUID) \
        -> ForecastSeriesTable | None:

    statement = select(ForecastSeriesTable) \
        .options(joinedload(ForecastSeriesTable._tags),
                 joinedload(ForecastSeriesTable.injectionplans)) \
        .where(ForecastSeriesTable.oid == forecastseries_oid)

    result = await db.execute(statement)

    return result.scalars().unique().one_or_none()


async def read_modelconfigs(db: AsyncSession,
                            tag_names: list[str]) \
        -> list[ModelConfigTable]:

    statement = select(ModelConfigTable).where(
        ModelConfigTable._tags.any(TagTable.name.in_(tag_names)))

    results = await db.execute(statement)

    return results.scalars().unique()


async def read_all_forecasts(db: AsyncSession,
                             forecastseries_oid: UUID) \
        -> list[ForecastTable]:

    statement = select(ForecastTable).where(
        ForecastTable.forecastseries_oid == forecastseries_oid)

    results = await db.execute(statement)

    return results.scalars().unique().all()


async def read_forecast_modelruns(db: AsyncSession, forecast_oid: UUID):

    # load Forecast, defer well&catalog
    # join model runs, defer injectionplan
    # subqueryload modelconfig, load only name
    statement = select(ForecastTable) \
        .options(
            joinedload(ForecastTable.modelruns)
            .subqueryload(ModelRunTable.modelconfig)
            .load_only(ModelConfigTable.name, ModelConfigTable.oid),
            joinedload(ForecastTable.modelruns)
            .subqueryload(ModelRunTable.injectionplan)
            .load_only(InjectionPlanTable.name, InjectionPlanTable.oid)
    ) \
        .where(ForecastTable.oid == forecast_oid)

    result = await db.execute(statement)

    return result.scalar()


async def read_forecastseries_modelconfigs(db: AsyncSession,
                                           forecastseries_oid: UUID) \
        -> list[ModelConfigTable]:

    statement = select(ModelConfigTable) \
        .join(ModelConfigTable._tags) \
        .options(joinedload(ModelConfigTable._tags))\
        .join(ForecastSeriesTable, TagTable.forecastseries) \
        .where(ForecastSeriesTable.oid == forecastseries_oid)

    results = await db.execute(statement)

    return results.scalars().unique().all()


async def read_forecastseries_injectionplans(
        db: AsyncSession,
        forecastseries_oid: UUID) -> list[InjectionPlanTable]:
    statement = select(InjectionPlanTable) \
        .where(InjectionPlanTable.forecastseries_oid == forecastseries_oid)

    result = await db.execute(statement)

    return result.scalars().unique()


async def read_forecast_injectionobservations(
        db: AsyncSession, forecast_oid: UUID):

    statement = select(InjectionObservationTable.data).where(
        InjectionObservationTable.forecast_oid == forecast_oid)

    result = await db.execute(statement)

    return result.scalar()


async def read_forecast_seismicityobservation(db: AsyncSession,
                                              forecast_oid: UUID):

    statement = select(SeismicityObservationTable.data).where(
        SeismicityObservationTable.forecast_oid == forecast_oid)

    result = await db.execute(statement)

    return result.scalar()


async def read_modelrun_modelconfig(db: AsyncSession, modelrun_oid: UUID):

    statement = select(ModelConfigTable) \
        .join(ModelRunTable,
              ModelRunTable.modelconfig_oid == ModelConfigTable.oid) \
        .options(joinedload(ModelConfigTable._tags)) \
        .where(ModelRunTable.oid == modelrun_oid)

    result = await db.execute(statement)

    return result.scalar()


async def read_injectionplan(db: AsyncSession, injectionplan_oid: UUID):

    statement = select(InjectionPlanTable.data).where(
        InjectionPlanTable.oid == injectionplan_oid)

    result = await db.execute(statement)

    return result.scalar()


async def read_modelrun_rates(db: AsyncSession, modelrun_id: UUID):

    statement = select(ModelRunTable) \
        .options(joinedload(ModelRunTable.modelconfig)
                 .load_only(ModelConfigTable.name, ModelConfigTable.oid),
                 joinedload(ModelRunTable.injectionplan)
                 .load_only(InjectionPlanTable.name, InjectionPlanTable.oid),
                 joinedload(ModelRunTable.modelresults).options(
            joinedload(ModelResultTable.timestep),
            joinedload(ModelResultTable.gridcell),
            joinedload(ModelResultTable.grparameters),
        )
    ) \
        .where(ModelRunTable.oid == modelrun_id)

    result = await db.execute(statement)

    return result.scalar()


async def read_forecast_rates(db: AsyncSession,
                              forecast_id: UUID,
                              modelconfigs: list[str] | None = None,
                              injectionplans: list[str] | None = None):

    statement = select(ModelRunTable) \
        .options(joinedload(ModelRunTable.modelconfig)
                 .load_only(ModelConfigTable.name, ModelConfigTable.oid),
                 joinedload(ModelRunTable.injectionplan)
                 .load_only(InjectionPlanTable.name, InjectionPlanTable.oid),
                 joinedload(ModelRunTable.modelresults).options(
            joinedload(ModelResultTable.timestep),
            joinedload(ModelResultTable.gridcell),
            joinedload(ModelResultTable.grparameters),
        )
    ) \
        .where(ModelRunTable.forecast_oid == forecast_id)

    if modelconfigs:
        statement = statement.join(ModelConfigTable).where(
            ModelConfigTable.name.in_(modelconfigs))

    if injectionplans:
        statement = statement.join(InjectionPlanTable).where(
            InjectionPlanTable.name.in_(injectionplans))

    result = await db.execute(statement)

    return result.scalars().unique()
