from uuid import UUID

from seismostats import ForecastCatalog

from hermes.repositories.results import (GridCellRepository,
                                         ModelResultRepository,
                                         TimeStepRepository)
from hermes.schemas import GridCell, TimeStep
from hermes.schemas.base import EResultType


def save_forecast_catalog_to_repositories(
        session,
        forecastseries_oid: UUID,
        modelrun_oid: UUID,
        forecast_catalog: ForecastCatalog) -> None:
    # create the timestep and gridcell objects
    timestep = TimeStep(starttime=forecast_catalog.starttime,
                        endtime=forecast_catalog.endtime,
                        forecastseries_oid=forecastseries_oid)
    griddcell = GridCell(geom=forecast_catalog.bounding_polygon,
                         forecastseries_oid=forecastseries_oid)

    # save the timestep and gridcell objects to the database
    timestep = TimeStepRepository.get_or_create(session, timestep)
    griddcell = GridCellRepository.get_or_create(session, griddcell)

    # create n_catalogs number of ModelResults
    ids = ModelResultRepository.batch_create(
        session,
        forecast_catalog.n_catalogs,
        EResultType.CATALOG,
        timestep.oid,
        griddcell.oid,
        modelrun_oid
    )

    # replace the catalog_id column with the modelresult_oids


def serialize_seismostats_forecastcatalog(
        forecast_catalog: ForecastCatalog) -> list[dict]:
    pass
