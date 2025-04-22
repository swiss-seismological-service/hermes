from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from hermes.datamodel.data_tables import (InjectionObservationTable,
                                          InjectionPlanTable,
                                          SeismicityObservationTable)
from hermes.datamodel.project_tables import ForecastTable, ModelConfigTable
from hermes.datamodel.result_tables import ModelResultTable, ModelRunTable


async def read_forecast_injectionobservation(
        db: AsyncSession, forecast_oid: UUID):

    statement = select(InjectionObservationTable.data).where(
        InjectionObservationTable.forecast_oid == forecast_oid)

    result = await db.execute(statement)

    return result.scalar()


async def read_forecast_seismicityobservation(db: AsyncSession,
                                              forecast_oid: UUID):

    statement = select(SeismicityObservationTable.data).where(
        SeismicityObservationTable.forecast_oid == forecast_oid)

    result = await db.execute(statement)

    return result.scalar()


async def read_modelrun_modelconfig(db: AsyncSession, modelrun_oid: UUID):

    statement = select(ModelConfigTable) \
        .join(ModelRunTable,
              ModelRunTable.modelconfig_oid == ModelConfigTable.oid) \
        .options(joinedload(ModelConfigTable._tags)) \
        .where(ModelRunTable.oid == modelrun_oid)

    result = await db.execute(statement)

    return result.scalar()


async def read_modelrun_rates(db: AsyncSession, modelrun_id: UUID):

    statement = select(ModelRunTable) \
        .options(joinedload(ModelRunTable.modelconfig)
                 .load_only(ModelConfigTable.name, ModelConfigTable.oid),
                 joinedload(ModelRunTable.injectionplan)
                 .load_only(InjectionPlanTable.name, InjectionPlanTable.oid),
                 joinedload(ModelRunTable.modelresults).options(
            joinedload(ModelResultTable.timestep),
            joinedload(ModelResultTable.gridcell),
            joinedload(ModelResultTable.grparameters),
        )
    ) \
        .where(ModelRunTable.oid == modelrun_id)

    result = await db.execute(statement)

    return result.scalar()


async def read_modelrun_catalog(db: AsyncSession, modelrun_id: UUID):
    # TODO: Very Slow
    statement = select(ModelRunTable) \
        .options(joinedload(ModelRunTable.modelconfig)
                 .load_only(ModelConfigTable.name, ModelConfigTable.oid),
                 joinedload(ModelRunTable.injectionplan)
                 .load_only(InjectionPlanTable.name, InjectionPlanTable.oid),
                 joinedload(ModelRunTable.modelresults).options(
            joinedload(ModelResultTable.timestep),
            joinedload(ModelResultTable.gridcell),
            joinedload(ModelResultTable.seismicevents),
        )
    ) \
        .where(ModelRunTable.oid == modelrun_id)

    result = await db.execute(statement)

    return result.scalar()


async def read_forecast_rates(db: AsyncSession,
                              forecast_id: UUID,
                              modelconfigs: list[str] | None = None,
                              injectionplans: list[str] | None = None):

    statement = select(ModelRunTable) \
        .options(joinedload(ModelRunTable.modelconfig)
                 .load_only(ModelConfigTable.name, ModelConfigTable.oid),
                 joinedload(ModelRunTable.injectionplan)
                 .load_only(InjectionPlanTable.name, InjectionPlanTable.oid),
                 joinedload(ModelRunTable.modelresults).options(
            joinedload(ModelResultTable.timestep),
            joinedload(ModelResultTable.gridcell),
            joinedload(ModelResultTable.grparameters),
        )
    ) \
        .where(ModelRunTable.forecast_oid == forecast_id)

    if modelconfigs:
        statement = statement.join(ModelConfigTable).where(
            ModelConfigTable.name.in_(modelconfigs))

    if injectionplans:
        statement = statement.join(InjectionPlanTable).where(
            InjectionPlanTable.name.in_(injectionplans))

    result = await db.execute(statement)

    return result.scalars().unique()


async def read_forecast_by_modelrun(db: AsyncSession, modelrun_oid: UUID):
    statement = select(ForecastTable) \
        .join(ModelRunTable) \
        .where(ModelRunTable.oid == modelrun_oid)

    result = await db.execute(statement)

    return result.scalar()


async def read_injectionplan_by_modelrun(db: AsyncSession, modelrun_oid: UUID):
    statement = select(InjectionPlanTable.data) \
        .join(ModelRunTable) \
        .where(ModelRunTable.oid == modelrun_oid)

    result = await db.execute(statement)

    return result.scalar()
