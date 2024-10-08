from uuid import UUID

from seismostats import Catalog
from sqlalchemy import insert
from sqlalchemy.orm import Session

from hermes.datamodel.data_tables import (EventObservationTable,
                                          InjectionObservationTable,
                                          InjectionPlanTable,
                                          SeismicityObservationTable)
from hermes.io.catalog import serialize_seismostats_catalog
from hermes.repositories.base import repository_factory
from hermes.schemas.data_schemas import (EventObservation,
                                         InjectionObservation, InjectionPlan,
                                         SeismicityObservation)


class EventObservationRepository(repository_factory(
        EventObservation, EventObservationTable)):
    @classmethod
    def create_from_catalog(cls,
                            session: Session,
                            data: Catalog,
                            seismicityobservation_oid: UUID) -> UUID:
        events = serialize_seismostats_catalog(data, EventObservation)

        session.execute(
            insert(EventObservationTable)
            .values(seismicityobservation_oid=seismicityobservation_oid),
            events)
        session.commit()

    @classmethod
    def create_from_quakeml(cls,
                            session: Session,
                            data: str,
                            seismicityobservation_oid: UUID) -> UUID:

        catalog = Catalog.from_quakeml(data,
                                       include_uncertainties=True,
                                       include_quality=True)

        cls.create_from_catalog(session, catalog, seismicityobservation_oid)


class SeismicityObservationRepository(repository_factory(
        SeismicityObservation, SeismicityObservationTable)):

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

        EventObservationRepository.create_from_catalog(
            session, data, object_db.oid)

        return object_db.oid

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

        EventObservationRepository.create_from_quakeml(
            session, data, object_db.oid)

        return object_db.oid


class InjectionObservationRepository(repository_factory(
        InjectionObservation, InjectionObservationTable)):
    pass


class InjectionPlanRepository(repository_factory(
        InjectionPlan, InjectionPlanTable)):
    pass
