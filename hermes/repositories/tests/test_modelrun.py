from hermes.repositories.results import ModelRunRepository
from hermes.schemas.base import EStatus
from hermes.schemas.result_schemas import ModelRun


class TestModelRun:
    def test_create(self, session):
        modelrun = ModelRun(status=EStatus.PENDING)
        modelrun = ModelRunRepository.create(session, modelrun)
        assert modelrun.oid is not None
