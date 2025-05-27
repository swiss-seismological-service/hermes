from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from hermes.datamodel.data_tables import (InjectionObservationTable,
                                          InjectionPlanTable,
                                          SeismicityObservationTable)
from hermes.datamodel.project_tables import (ForecastSeriesTable,
                                             ForecastTable, ModelConfigTable,
                                             ProjectTable, TagTable)
from hermes.datamodel.result_tables import ModelRunTable
from hermes.schemas import Forecast, ForecastSeries, ModelConfig, Project, Tag
from web.repositories.base import async_repository_factory
from web.schemas import ForecastJSON


class AsyncProjectRepository(async_repository_factory(Project, ProjectTable)):
    pass


class AsyncTagRepository(async_repository_factory(
        Tag, TagTable)):
    pass


class AsyncForecastSeriesRepository(async_repository_factory(
        ForecastSeries, ForecastSeriesTable)):

    @classmethod
    async def get_by_project(cls,
                             session: AsyncSession,
                             project_oid: str,
                             joined_attrs: list[str] | None = None,
                             override_model: BaseModel | None = None) \
            -> list[ForecastSeries]:
        q = select(ForecastSeriesTable).where(
            ForecastSeriesTable.project_oid == project_oid)
        if joined_attrs:
            for attr in joined_attrs:
                q = q.options(joinedload(getattr(ForecastSeriesTable, attr)))
        result = await session.execute(q)
        result = result.unique().scalars().all()
        model = override_model or cls.model
        return [model.model_validate(f) for f in result]

    @classmethod
    async def get_by_id(cls,
                        session: AsyncSession,
                        forecastseries_oid: str,
                        joined_attrs: list[str] | None = None,
                        override_model: BaseModel | None = None) \
            -> ForecastSeries:

        q = select(ForecastSeriesTable).where(
            ForecastSeriesTable.oid == forecastseries_oid)
        if joined_attrs:
            for attr in joined_attrs:
                q = q.options(joinedload(getattr(ForecastSeriesTable, attr)))
        result = await session.execute(q)
        result = result.unique().scalar_one_or_none()
        model = override_model or cls.model
        return model.model_validate(result) if result else None


class AsyncForecastRepository(async_repository_factory(Forecast,
                                                       ForecastTable)):

    joined_load_query = (
        joinedload(ForecastTable.injectionobservation)
        .load_only(InjectionObservationTable.oid),
        joinedload(ForecastTable.seismicityobservation)
        .load_only(SeismicityObservationTable.oid),
        joinedload(ForecastTable.modelruns)
        .options(
            joinedload(ModelRunTable.modelconfig)
            .load_only(ModelConfigTable.oid,
                       ModelConfigTable.result_type,
                       ModelConfigTable.name),
            joinedload(ModelRunTable.injectionplan)
            .load_only(InjectionPlanTable.name,
                       InjectionPlanTable.oid)
        ).load_only(ModelRunTable.oid,
                    ModelRunTable.status))

    @classmethod
    async def get_by_forecastseries_joined(
            cls,
            session: AsyncSession,
            forecastseries_oid: str) -> list[ForecastJSON]:
        """
        Gets Forecasts by ForecastSeries with joined information down to the
        ModelRun level. This is used to get all the information needed to
        efficiently navigate the Forecastseries' Forecasts and results.
        """
        q = (select(ForecastTable)
             .where(ForecastTable.forecastseries_oid == forecastseries_oid)
             .options(*cls.joined_load_query))

        result = await session.execute(q)
        result = result.unique().scalars().all()
        return [ForecastJSON.model_validate(r) for r in result]

    @classmethod
    async def get_by_id_joined(
            cls,
            session: AsyncSession,
            oid: str) -> ForecastJSON:
        """
        Gets Forecasts by ForecastSeries with joined information down to the
        ModelRun level. This is used to get all the information needed to
        efficiently navigate the Forecastseries' Forecasts and results.
        """
        q = (
            select(ForecastTable)
            .where(ForecastTable.oid == oid)
            .options(*cls.joined_load_query)
        )
        result = await session.execute(q)
        result = result.unique().scalar()
        return ForecastJSON.model_validate(result) if result else None

    @classmethod
    async def get_by_modelrun(
            cls,
            session: AsyncSession,
            modelrun_oid: str) -> list[Forecast]:
        q = select(ForecastTable) \
            .join(ModelRunTable) \
            .where(ModelRunTable.oid == modelrun_oid)
        result = await session.execute(q)
        result = result.scalar()
        return cls.model.model_validate(result) if result else None


class AsyncModelConfigRepository(async_repository_factory(
        ModelConfig, ModelConfigTable)):

    @classmethod
    async def get_by_tags(cls,
                          session: AsyncSession,
                          tag_names: list[str]) -> list[ModelConfig]:
        q = select(ModelConfigTable).where(
            ModelConfigTable._tags.any(TagTable.name.in_(tag_names)))

        result = await session.execute(q)
        result = result.unique().scalars().all()
        return [cls.model.model_validate(m) for m in result]

    @classmethod
    async def get_by_modelrun(cls,
                              session: AsyncSession,
                              modelrun_oid: str) -> list[ModelConfig]:
        q = select(ModelConfigTable).join(
            ModelRunTable).where(ModelRunTable.oid == modelrun_oid)
        result = await session.execute(q)
        result = result.scalar()
        return cls.model.model_validate(result) if result else None
