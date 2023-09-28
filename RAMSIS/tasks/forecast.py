import json
import time
from datetime import datetime
from typing import List, Optional

from marshmallow import EXCLUDE
from prefect import task, get_run_logger
from prefect.tasks import exponential_backoff
from prefect.server.schemas.states import Failed
from ramsis.datamodel import EInput, EStatus, \
    Forecast, Project
from ramsis.io.sfm import (SFMWorkerIMessageSerializer,
                           SFMWorkerOMessageDeserializer)

from RAMSIS.db import session_handler
from RAMSIS.core.datasources import FDSNWSDataSource, HYDWSDataSource
from RAMSIS.core.worker.sfm import RemoteSeismicityWorkerHandle
from RAMSIS.db_utils import get_forecast, get_model_run
from RAMSIS.error import RemoteWorkerError


datetime_format = '%Y-%m-%dT%H:%M:%S.%f'


@task(task_run_name="run_forecast_flow(forecast{forecast_id})")
def forecast_status(forecast_id: int, connection_string: str) -> bool:
    """
    If forecast is not complete, return True.
    """
    with session_handler(connection_string) as session:
        forecast = get_forecast(forecast_id, session)
        return forecast.status.state


def any_model_runs_complete(
        forecast: Forecast) -> bool:
    """Return True if any model runs are complete"""
    logger = get_run_logger()
    model_run_complete = any([r.id for r in forecast.runs if
                              r.status.state == EStatus.COMPLETE])
    if model_run_complete:
        logger.warning("At least one model run has a COMPLETE status "
                       "which means that datasources will not be "
                       "refreshed")
        return True
    return False


@task(task_run_name="update_running(forecast{forecast_id})")
def update_running(forecast_id: int, connection_string: str) -> None:
    """
    Update forecast to running
    """
    with session_handler(connection_string) as session:
        forecast = get_forecast(forecast_id, session)
        forecast.status.state = EStatus.RUNNING
        session.commit()


@task(task_run_name="update_fdsn(forecast{forecast_id})")
def update_fdsn(forecast_id: int, dttime: datetime,
                connection_string: str) -> None:
    """
    Updates the catalog if the url is configured and
    a catalog is optional/required
    """
    def fetch_fdsn(url: str, project: Project,
                   forecast: Forecast) -> bytes:
        logger = get_run_logger()
        logger.info("Fetch fdsn called")
        # Do we want timeout to be configurable? Does this timeout
        # also cover contacting the webservice?
        seismics_data_source = FDSNWSDataSource(
            url, timeout=700)
        seismics_data_source.enabled = True

        starttime = datetime.strftime(project.starttime, datetime_format)
        endtime = datetime.strftime(forecast.starttime, datetime_format)

        cat = seismics_data_source.fetch(
            starttime=starttime,
            endtime=endtime)
        return cat

    with session_handler(connection_string) as session:
        logger = get_run_logger()
        forecast = get_forecast(forecast_id, session)
        forecastseries = forecast.forecastseries
        project = forecastseries.project
        if project.seismiccatalog:
            logger.info("Project has catalog, this will be used for the "
                        "forecast")
            forecast.seismiccatalog = project.seismiccatalog
            session.commit()
            return
        # Check if catalog is required and url is provided
        catalog_used = project.seismiccatalog_required in \
            [EInput.REQUIRED, EInput.OPTIONAL]
        fdsnws_url = project.fdsnws_url

        if catalog_used and fdsnws_url:
            if any_model_runs_complete(forecast):
                logger.info("Some model runs are complete, therefore "
                            "no seismic catalog will be fetched.")
                return
            logger.info("A catalog is required and a url is specified: "
                        f"{fdsnws_url}")
            # Delete existing seismic catalog if it exsits, so that the most
            # up to date one is used
            existing_catalog = forecast.seismiccatalog
            if existing_catalog:
                logger.info("updating seismic catalog on forecast")

            cat = fetch_fdsn(fdsnws_url, project, forecast)
            if not cat:
                cat = bytes("", "utf-8")
                logger.warning(
                    "An empty catalog has been created as no "
                    "catalog has been returned from the FDSN web service.")
            else:
                logger.info("A catalog has been returned with "
                            f"character length: {len(cat)}")

            forecast.seismiccatalog = cat
            session.commit()
        elif not forecast.catalog:
            if project.seismiccatalog_required == EInput.OPTIONAL:
                logger.info("No seismic catalog will be attached to the "
                            "forecast")
            elif project.seismiccatalog_required == EInput.NOT_ALLOWED:
                logger.info("No seismic catalog allowed for forecast.")


@task(task_run_name="update_hyd(forecast{forecast_id})")
def update_hyd(forecast_id: int, dttime: datetime,
               connection_string: str) -> None:
    """
    Updates the hydraulic history if the url is configured and
    a hydraulics are optional/required
    """
    def fetch_hyd(url: str, project: Project,
                  forecast: Forecast) -> dict:
        logger = get_run_logger()
        logger.info("Fetch hydws called")
        hydraulics_data_source = HYDWSDataSource(
            url, timeout=300)
        hydraulics_data_source.enabled = True

        starttime = datetime.strftime(project.starttime, datetime_format)
        endtime = datetime.strftime(forecast.starttime, datetime_format)

        well = hydraulics_data_source.fetch(
            starttime=starttime,
            endtime=endtime,
            level='hydraulic')
        return well

    with session_handler(connection_string) as session:
        logger = get_run_logger()
        forecast = get_forecast(forecast_id, session)
        forecastseries = forecast.forecastseries
        project = forecastseries.project
        hydws_url = project.hydws_url
        if project.injectionwell:
            logger.info("Project has injectionwell, this will be used for the "
                        "forecast")
            forecast.injectionwell = project.injectionwell
            session.commit()
            return
        well_used = project.injectionwell_required in \
            [EInput.REQUIRED, EInput.OPTIONAL]

        if well_used and hydws_url:
            if any_model_runs_complete(forecast):
                logger.info("Some model runs are complete, therefore "
                            "no injection well will be fetched.")
                return
            logger.info("A well is required and a url is specified: "
                        f"{hydws_url}")
            if forecast.injectionwell:
                logger.debug("modifying injection well on forecast")

            well = fetch_hyd(hydws_url, project, forecast)
            # We expect wells to be stored within lists by default
            forecast.injectionwell = json.dumps([well], ensure_ascii=False).\
                encode('utf-8')
            session.commit()
        elif not forecast.injectionwell:
            if project.injectionwell_required == EInput.OPTIONAL:
                logger.info("No observed well will be attached to the "
                            "forecast")
            elif project.injectionwell_required == EInput.NOT_ALLOWED:
                logger.info("No well allowed for forecast.")


@task(task_run_name="model_runs(scenario{forecast_id})")
def model_runs(
        forecast_id: int,
        connection_string: str) -> List[int]:
    with session_handler(connection_string) as session:
        forecast = get_forecast(forecast_id, session)
        model_run_ids = [r.id for r in forecast.runs if
                         r.status.state != EStatus.COMPLETE]
    return model_run_ids


@task(task_run_name="model_run_executor(forecast{forecast_id}_model_run)",
      tags=["model_run"])
def model_run_executor(forecast_id: int,
                       model_run_id: dict, connection_string: str) -> int:
    """
    Executes a single seimicity model run

    The executor instantiates the actual model that is associated with the run,
    connects to its status update signal and then calls its run method.
    """
    TASK_ACCEPTED = 202

    with session_handler(connection_string) as session:
        logger = get_run_logger()
        model_run = get_model_run(model_run_id, session)
        model_run.status.state = EStatus.RUNNING
        session.commit()
        model_config = model_run.modelconfig
        injection_plan = model_run.injectionplan
        forecast = model_run.forecast
        forecastseries = forecast.forecastseries

        serializer = SFMWorkerIMessageSerializer()
        payload = {
            'data': {
                "worker_config": {
                    "model_name": model_config.name,
                    "model_description": model_config.description,
                    "model_module": model_config.sfm_module,
                    "model_class": model_config.sfm_class},
                'attributes': {
                    'geometry_extent': forecastseries.geometryextent,
                    'altitude_min': forecastseries.altitudemin,
                    'altitude_max': forecastseries.altitudemax,
                    'seismic_catalog': forecast.seismiccatalog,
                    'injection_well': forecast.injectionwell,
                    'forecast_start': forecast.starttime,
                    'forecast_end': forecast.endtime,
                    'injection_plan': injection_plan,
                    'model_config': model_config.config}}}

        data = json.dumps(serializer._serialize_dict(payload))

        _worker_handle = RemoteSeismicityWorkerHandle.from_run(
            model_run)
        try:
            resp = _worker_handle.compute(
                data,
                deserializer=SFMWorkerOMessageDeserializer(unknown=EXCLUDE))
            logger.info(f"response of seismicity worker: {resp}")
        except RemoteSeismicityWorkerHandle.RemoteWorkerError as err:
            raise RemoteWorkerError(
                "model run submission has failed with "
                "error: RemoteWorkerError. Check if remote worker is"
                f" accepting requests. {err}")

        status = resp['data']['attributes']['status_code']

        if status != TASK_ACCEPTED:
            raise RemoteWorkerError(f"model run {resp['data']['task_id']} "
                                    f"has returned an error: {resp}")

        model_run.runid = resp['data']['task_id']
        model_run.status.state = EStatus.DISPATCHED
        session.commit()
        logger.info("returning model run id from model run task")
        return int(model_run.id)

@task(task_run_name="check_model_run_not_complete(model_run{model_run_id})") # noqa
def check_model_run_not_complete(
        model_run_id: int,
        connection_string: str) -> Optional[int]:
    with session_handler(connection_string) as session:
        logger = get_run_logger()
        model_run = get_model_run(model_run_id, session)
        if model_run.status.state == EStatus.DISPATCHED:
            return model_run_id
        elif model_run.status.state == EStatus.COMPLETE:
            logger.info("The model run is complete.")
        elif model_run.status.state == EStatus.FINISHED_WITH_ERRORS:
            logger.info("The model run is in a state of error")
        else:
            logger.info("The model run is in an unknown state: "
                        f"{model_run.status.state}")
        return None


@task
def waiting_task(
        forecast_id: int,
        seconds_to_wait: float,
        connection_string: str) -> Optional[int]:
    # In order to avoid a long wait at the end, only sleep if the model
    # run is still in progress.
    with session_handler(connection_string) as session:
        logger = get_run_logger()
        forecast = get_forecast(forecast_id, session)
        if any(model_run.status.state == EStatus.DISPATCHED
               for model_run in forecast.runs):
            logger.info(f"sleeping for {seconds_to_wait} seconds...")
            time.sleep(seconds_to_wait)
        else:
            pass

@task(task_run_name="check_model_runs_dispatched(forecast_{forecast_id})") # noqa
def check_model_runs_dispatched(
        forecast_id: int,
        connection_string: str) -> bool:
    with session_handler(connection_string) as session:
        logger = get_run_logger()
        logger.info(f"check model runs dispatched forecast_id: {forecast_id}")
        forecast = get_forecast(forecast_id, session)
        all_statuses = [r.status.state for r in forecast.runs]
        logger.info(f"In checking dispatched, forecast: {forecast_id}, "
                    f"statuses: {all_statuses}")
        if EStatus.DISPATCHED in all_statuses:
            logger.debug("EStatus.DISPATCHED in all statuses")
            return True
        logger.debug("EStatus.DISPATCHED not in all statuses, quitting loop")
        return False


@task(tags=["model_run"],
      task_run_name="poll_model_run(forecast{forecast_id}_model_run{model_run_id})", # noqa
      retries=3,
      retry_delay_seconds=exponential_backoff(backoff_factor=10),
      retry_jitter_factor=1,
      timeout_seconds=100
      ) # noqa
def poll_model_run(forecast_id: int, model_run_id: int,
                   connection_string: str) -> None:
    """
    Executes a single seimicity model run

    The executor instantiates the actual model that is associated with the run,
    connects to its status update signal and then calls its run method.
    """
    TASK_ACCEPTED = 202
    TASK_PROCESSING = 423
    TASK_COMPLETE = 200
    TASK_ERROR = [418, 204, 405, 422, 500]
    with session_handler(connection_string) as session:
        logger = get_run_logger()
        model_run = get_model_run(model_run_id, session)
        if model_run.status.state in (
                EStatus.COMPLETE,
                EStatus.FINISHED_WITH_ERRORS):
            logger.info("model run is complete or has errors, exiting")
            return
        logger.info(f"Polling for runid={model_run.runid}")

        _worker_handle = RemoteSeismicityWorkerHandle.from_run(
            model_run)

        deserializer = SFMWorkerOMessageDeserializer(
            many=True)
        try:
            logger.info("getting response from worker")
            resp = _worker_handle.query(
                task_ids=model_run.runid,
                deserializer=deserializer).first()
            logger.info("after getting response from worker")
        except RemoteSeismicityWorkerHandle.RemoteWorkerError as err:
            model_run.status.state = EStatus.FINISHED_WITH_ERRORS
            return Failed(message=err)
        except RemoteSeismicityWorkerHandle.HTTPError as err:
            model_run.status.state = EStatus.FINISHED_WITH_ERRORS
            return Failed(message=err)
        else:
            logger.info(f"type of resp: {type(resp), len(resp)}")
            status = resp['data']['attributes']['status_code']
            logger.info(f"status code of model run: {status}")
            status_bool = status in (TASK_ACCEPTED, TASK_PROCESSING)
            status_bool_complete = status == TASK_COMPLETE
            logger.info(f"status_bool: {status_bool}")
            logger.info(f"status_bool complete: {status_bool_complete}")

            if status in (TASK_ACCEPTED, TASK_PROCESSING):
                logger.info("status in accepted or processing")
                return

            logger.info(
                f'Received response (run={model_run!r}, '
                f'runid={model_run.runid}): {resp}')
            if status == TASK_COMPLETE:
                try:
                    result = resp['data']['attributes']['forecast']
                except KeyError:
                    logger.error(
                        "Remote Seismicity Worker has not returned "
                        f"a forecast (runid={model_run.runid}: "
                        f"{resp})")
                    model_run.status.state = EStatus.FINISHED_WITH_ERRORS
                    session.commit()
                except Exception:
                    logger.error("EXCEPTION! setting model run to finished "
                                 "with errors")
                    model_run.status.state = EStatus.FINISHED_WITH_ERRORS
                    session.commit()

                else:
                    model_run.resulttimebins = result
                    logger.debug("setting model run to complete.")
                    model_run.status.state = EStatus.COMPLETE
                    session.commit()

            elif status in TASK_ERROR:
                logger.error("EXCEPTION! task error. setting model run "
                             "to finished with errors")
                model_run.status.state = EStatus.FINISHED_WITH_ERRORS
                session.commit()
                logger.error("Remote Seismicity Model Worker"
                             " has returned an unsuccessful status code."
                             f"(runid={model_run.runid}: {resp})")

            else:
                logger.error(f"Unhandled status code recieved: {status}")
                model_run.status.state = EStatus.FINISHED_WITH_ERRORS
                session.commit()
                logger.error(
                    "Remote Seismicity Model Worker"
                    " has returned an unhandled status code."
                    f"(runid={model_run.runid}: {resp})")
