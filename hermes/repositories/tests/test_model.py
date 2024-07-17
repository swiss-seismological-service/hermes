import json
import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from hermes.repositories.model import ModelConfigRepository
from hermes.schemas import ModelConfig

MODULE_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data')


class TestModel:

    def test_create(self, connection, session):
        with open(os.path.join(MODULE_LOCATION, 'model.json')) as f:
            model_config = ModelConfig(name='config', **json.load(f))

        model_config = ModelConfigRepository.create(session, model_config)

        assert model_config.oid is not None
        assert 'FORGE' in model_config.tags

        tags = connection.execute(
            text('SELECT * FROM tag'))
        tags = [t.name for t in tags.all()]
        assert len(tags) == 2
        assert "INDUCED" in tags

    def test_unique(self, session):
        with open(os.path.join(MODULE_LOCATION, 'model.json')) as f:
            model_config = ModelConfig(name='config', **json.load(f))

        ModelConfigRepository.create(session, model_config)

        with pytest.raises(IntegrityError):
            ModelConfigRepository.create(session, model_config)
