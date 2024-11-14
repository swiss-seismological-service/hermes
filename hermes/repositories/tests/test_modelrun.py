import json
import os

from hermes.repositories.data import InjectionPlanRepository
from hermes.repositories.results import ModelRunRepository
from hermes.schemas.base import EStatus
from hermes.schemas.result_schemas import ModelRun

MODULE_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data')


class TestModelRun:
    def test_create(self, session):
        modelrun = ModelRun(status=EStatus.PENDING)
        modelrun = ModelRunRepository.create(session, modelrun)
        assert modelrun.oid is not None

    def test_delete_orphans(self, session):
        with open(os.path.join(MODULE_LOCATION, 'hydraulics.json'), 'rb') as f:
            [data] = json.load(f)

        injectionplan_oid = InjectionPlanRepository.create_from_hydjson(
            session, json.dumps(data), 'test_injectionplan')

        modelrun1 = ModelRun(status=EStatus.PENDING,
                             injectionplan_oid=injectionplan_oid)
        modelrun1 = ModelRunRepository.create(session, modelrun1)

        modelrun2 = ModelRun(status=EStatus.PENDING,
                             injectionplan_oid=injectionplan_oid)
        modelrun2 = ModelRunRepository.create(session, modelrun2)

        ModelRunRepository.delete(session, modelrun1.oid)

        assert InjectionPlanRepository.get_by_id(
            session, injectionplan_oid) is not None

        ModelRunRepository.delete(session, modelrun2.oid)

        assert InjectionPlanRepository.get_by_id(
            session, injectionplan_oid) is None
