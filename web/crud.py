from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hermes.datamodel import ProjectTable


async def read_all_projects(db: AsyncSession,
                            starttime: datetime | None = None) \
        -> list[ProjectTable]:

    statement = select(ProjectTable)

    if starttime:
        statement = statement.filter(ProjectTable.starttime > starttime)

    results = await db.execute(statement)

    return results.scalars().unique().all()


async def read_project(db: AsyncSession,
                       project_id: int) -> \
        ProjectTable | None:

    statement = select(ProjectTable).where(ProjectTable.id == project_id)

    result = await db.execute(statement)

    return result.scalars().unique().one_or_none()
