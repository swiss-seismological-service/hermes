from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from hermes.datamodel import ProjectTable
from hermes.datamodel.data_tables import InjectionPlanTable
from hermes.datamodel.project_tables import (ForecastSeriesTable,
                                             ForecastTable, ModelConfigTable,
                                             TagTable)
from hermes.datamodel.result_tables import ModelRunTable


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
            # defer(ForecastTable.injectionobservation, raiseload=True),
            # defer(ForecastTable.seismicityobservation, raiseload=True),
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
