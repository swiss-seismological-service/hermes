from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from hermes.datamodel import ProjectTable
from hermes.datamodel.project_tables import (ForecastSeriesTable,
                                             ModelConfigTable, TagTable)


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


async def read_modelconfigs(db: AsyncSession,
                            tag_names: list[str]) \
        -> list[ModelConfigTable]:

    statement = select(ModelConfigTable).where(
        ModelConfigTable._tags.any(TagTable.name.in_(tag_names)))

    results = await db.execute(statement)

    return results.scalars().unique()
