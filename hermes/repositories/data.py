from uuid import UUID

from seismostats import Catalog
from sqlalchemy.orm import Session

from hermes.datamodel.data_tables import (InjectionObservationTable,
                                          InjectionPlanTable,
                                          SeismicityObservationTable)
from hermes.repositories.base import repository_factory
from hermes.schemas.data_schemas import (InjectionObservation, InjectionPlan,
                                         SeismicityObservation)


class SeismicityObservationRepository(repository_factory(
        SeismicityObservation, SeismicityObservationTable)):

    # TODO: implement creation of EventObservations
    @classmethod
    def create_from_catalog(cls,
                            session: Session,
                            data: Catalog,
                            forecast_oid: UUID) -> UUID:
        qml = data.to_quakeml()
        object_db = SeismicityObservation(
            data=qml,
            forecast_oid=forecast_oid
        )
        object_db = cls.create(session, object_db)
        return object_db.oid

    # TODO: implement creation of EventObservations
    @classmethod
    def create_from_quakeml(cls,
                            session: Session,
                            data: str,
                            forecast_oid: UUID) -> UUID:
        object_db = SeismicityObservation(
            data=data,
            forecast_oid=forecast_oid
        )
        object_db = cls.create(session, object_db)
        return object_db.oid


class InjectionObservationRepository(repository_factory(
        InjectionObservation, InjectionObservationTable)):
    pass


class InjectionPlanRepository(repository_factory(
        InjectionPlan, InjectionPlanTable)):
    pass
