from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hermes.datamodel import TagTable
from hermes.repositories import repository_factory
from hermes.schemas import Tag


class TagRepository(repository_factory(
        Tag, TagTable)):

    @classmethod
    def _get_by_name(cls, session: Session, name: str) -> TagTable:
        q = select(TagTable).where(TagTable.name == name)
        result = session.execute(q).unique().scalar_one_or_none()
        return result

    @classmethod
    def get_by_name(cls, session: Session, name: str) -> Tag:
        result = cls._get_by_name(session, name)
        return cls.model.model_validate(result) if result else None

    @classmethod
    def _get_or_create(cls, session: Session, name: str) -> TagTable:
        q = select(TagTable).where(TagTable.name == name)
        result = session.execute(q).unique().scalar_one_or_none()
        if not result:
            try:
                result = TagTable(name=name)
                session.add(result)
                session.commit()
                session.refresh(result)
            except IntegrityError as e:
                session.rollback()
                result = cls._get_by_name(session, name)
                if not result:
                    raise e
        return result

    @classmethod
    def get_or_create(cls, session: Session, name: str) -> Tag:
        result = cls._get_or_create(session, name)
        return cls.model.model_validate(result) if result else None
