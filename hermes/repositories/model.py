from sqlalchemy import select
from sqlalchemy.orm import Session

from hermes.datamodel import ModelConfigTable, TagTable
from hermes.repositories import repository_factory
from hermes.schemas import ModelConfig


class ModelConfigRepository(repository_factory(
        ModelConfig, ModelConfigTable)):

    @classmethod
    def create(cls, session: Session, data: ModelConfig) -> ModelConfig:

        tags = []

        for tag in data.tags:
            q = select(TagTable).where(TagTable.name == tag)
            result = session.execute(q).unique().scalar_one_or_none()
            if result:
                tags.append(result)
            else:
                tags.append(TagTable(name=tag))

        db_model = ModelConfigTable(
            _tags=tags, **data.model_dump(exclude_unset=True,
                                          exclude=['tags']))
        session.add(db_model)
        session.commit()
        session.refresh(db_model)
        return cls.model.model_validate(db_model)
