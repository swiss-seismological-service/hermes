from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from hermes.datamodel import ORMBase
from hermes.schemas import Model


def repository_factory(model: Model, orm_model: ORMBase):

    class RepositoryBase:
        model: Model
        orm_model: ORMBase

        @classmethod
        def create(cls, session: Session, data: Model) -> Model:
            db_model = cls.orm_model(**data.model_dump(exclude_unset=True))
            session.add(db_model)
            session.commit()
            session.refresh(db_model)
            return cls.model.model_validate(db_model)

        @classmethod
        def get_by_id(cls, session: Session, oid: str | UUID) -> Model:
            q = select(cls.orm_model).where(
                getattr(cls.orm_model, 'oid') == oid)
            result = session.execute(q).unique().scalar_one_or_none()
            return cls.model.model_validate(result) if result else None

        @classmethod
        def get_all(cls, session: Session) -> list[Model]:
            q = select(cls.orm_model)
            result = session.execute(q).scalars().all()
            return [cls.model.model_validate(row) for row in result]

    RepositoryBase.model = model
    RepositoryBase.orm_model = orm_model

    return RepositoryBase
