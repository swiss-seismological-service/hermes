from sqlalchemy import select
from sqlalchemy.orm import Session

from hermes.datamodel import TagTable
from hermes.repositories import repository_factory
from hermes.schemas import Tag


class TagRepository(repository_factory(
        Tag, TagTable)):

    @classmethod
    def _get_or_create(cls, session: Session, name: str) -> TagTable:
        q = select(TagTable).where(TagTable.name == name)
        result = session.execute(q).unique().scalar_one_or_none()
        if not result:
            result = TagTable(name=name)
            session.add(result)
            session.commit()
            session.refresh(result)
        return result

    @classmethod
    def get_or_create(cls, session: Session, name: str) -> Tag:
        result = cls._get_or_create(session, name)
        return cls.model.model_validate(result)
