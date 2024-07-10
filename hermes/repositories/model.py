from sqlalchemy.orm import Session

from hermes.datamodel import ModelConfigTable
from hermes.repositories import repository_factory
from hermes.repositories.tag import TagRepository
from hermes.schemas import ModelConfig


class ModelConfigRepository(repository_factory(
        ModelConfig, ModelConfigTable)):

    @classmethod
    def create(cls, session: Session, data: ModelConfig) -> ModelConfig:

        # Check if tags exist in the database, if not create them.
        tags = []
        for tag in data.tags:
            tags.append(TagRepository._get_or_create(session, tag))

        # Create the database model and commit it to the database.
        db_model = ModelConfigTable(
            _tags=tags, **data.model_dump(exclude_unset=True,
                                          exclude=['tags']))
        session.add(db_model)
        session.commit()
        session.refresh(db_model)
        return cls.model.model_validate(db_model)
