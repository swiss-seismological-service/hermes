
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from hermes.datamodel.data_tables import (InjectionObservationTable,
                                          InjectionPlanTable,
                                          SeismicityObservationTable)
from hermes.datamodel.result_tables import ModelRunTable
from hermes.schemas.data_schemas import (InjectionObservation, InjectionPlan,
                                         SeismicityObservation)
from web.repositories.base import async_repository_factory


class AsyncSeismicityObservationRepository(async_repository_factory(
        SeismicityObservation, SeismicityObservationTable)):

    @classmethod
    async def get_by_forecast(
            cls,
            session: Session,
            forecast_oid: UUID) -> SeismicityObservation:

        q = select(SeismicityObservationTable).where(
            SeismicityObservationTable.forecast_oid == forecast_oid)
        result = await session.execute(q)
        result = result.scalar()
        return cls.model.model_validate(result) if result else None


class AsyncInjectionObservationRepository(async_repository_factory(
        InjectionObservation, InjectionObservationTable)):

    @classmethod
    async def get_by_forecast(
            cls,
            session: Session,
            forecast_oid: UUID) -> InjectionObservation:

        q = select(InjectionObservationTable).where(
            InjectionObservationTable.forecast_oid == forecast_oid)
        result = await session.execute(q)
        result = result.scalar()
        return cls.model.model_validate(result)


class AsyncInjectionPlanRepository(async_repository_factory(
        InjectionPlan, InjectionPlanTable)):

    @classmethod
    async def get_by_forecastseries(
            cls,
            session: Session,
            forecastseries_oid: UUID) -> InjectionPlan:

        q = select(InjectionPlanTable).where(
            InjectionPlanTable.forecastseries_oid == forecastseries_oid)
        result = await session.execute(q)
        result = result.scalars().unique()
        return [cls.model.model_validate(f) for f in result]

    @classmethod
    async def get_by_modelrun(
            cls,
            session: Session,
            modelrun_id: UUID) -> InjectionPlan:

        q = select(InjectionPlanTable) \
            .join(ModelRunTable) \
            .where(ModelRunTable.oid == modelrun_id)

        result = await session.execute(q)
        result = result.scalar()
        return cls.model.model_validate(result) if result else None
