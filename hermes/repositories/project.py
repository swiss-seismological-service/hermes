from sqlalchemy import select
from sqlalchemy.orm import Session

from hermes.datamodel import ProjectTable
from hermes.repositories import repository_factory
from hermes.schemas import Project


class ProjectRepository(repository_factory(Project, ProjectTable)):

    @classmethod
    def get_by_name(cls, session: Session, name: str) -> Project:
        q = select(ProjectTable).where(ProjectTable.name == name)
        result = session.execute(q).unique().scalar_one_or_none()
        return cls.model.model_validate(result) if result else None
