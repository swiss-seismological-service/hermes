from hermes.datamodel import ModelRunTable
from hermes.repositories import repository_factory
from hermes.schemas import ModelRun


class ModelRunRepository(repository_factory(
        ModelRun, ModelRunTable)):
    pass
