from seismostats import ForecastCatalog

from hermes.schemas import GridCell, TimeStep


def save_forecast_catalog_to_repositories(
        session,
        forecast_catalog: ForecastCatalog) -> None:
    # create the timestep and gridcell objects
    timestep = TimeStep(starttime=forecast_catalog.starttime,
                        endtime=forecast_catalog.endtime)
    griddcell = GridCell(geom=forecast_catalog.bounding_polygon)

    # create n_catalogs number of ModelResults
    # replace the catalog_id column with the modelresult_oids


def serialize_seismostats_forecastcatalog(
        forecast_catalog: ForecastCatalog) -> list[dict]:
    pass
