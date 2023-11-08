import json
import time
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm.session import Session
from marshmallow import EXCLUDE
from prefect import task, get_run_logger
from prefect.tasks import exponential_backoff
from prefect.server.schemas.states import Failed
from ramsis.datamodel import EInput, EStatus, \
    Forecast, Project
from ramsis.io.sfm import (SFMWorkerIMessageSerializer,
                           SFMWorkerOMessageDeserializer)

from RAMSIS.db import session_handler
from RAMSIS.clients.datasources import FDSNWSDataSource, HYDWSDataSource
from RAMSIS.clients.sfm import RemoteSeismicityWorkerHandle
from RAMSIS.db_utils import get_forecast, get_model_run
from RAMSIS.tasks.utils import fork_log


datetime_format = '%Y-%m-%dT%H:%M:%S.%f'


@task(task_run_name="run_forecast_flow(forecast{forecast_id})")
def forecast_status(forecast_id: int, connection_string: str) -> bool:
    """
    If forecast is not complete, return True.
    """
    with session_handler(connection_string) as session:
        forecast = get_forecast(forecast_id, session)
        return forecast.status


def any_model_runs_complete(
        forecast: Forecast, session: Session) -> bool:
    """Return True if any model runs are complete"""
    logger = get_run_logger()
    model_run_complete = any([r.id for r in forecast.runs if
                              r.status == EStatus.COMPLETED])
    if model_run_complete:
        msg = ("At least one model run has a COMPLETED status "
               "which means that datasources will not be "
               "refreshed")
        logger.warning(msg)
        forecast.add_log(msg)
        session.commit()
        return True
    return False


@task(task_run_name="update_running(forecast{forecast_id})")
def update_running(forecast_id: int, connection_string: str) -> None:
    """
    Update forecast to running
    """
    with session_handler(connection_string) as session:
        forecast = get_forecast(forecast_id, session)
        forecast.status = EStatus.RUNNING
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
        seismics_data_source = FDSNWSDataSource(
            url, timeout=700)

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
            forecast.seismiccatalog = project.seismiccatalog
            session.commit()
            msg = ("Project has catalog, this will be used for the "
                   "forecast")
            fork_log(forecast, EStatus.RUNNING, msg, session, logger)
            return
        # Check if catalog is required and url is provided
        catalog_used = project.seismiccatalog_required in \
            [EInput.REQUIRED, EInput.OPTIONAL]
        fdsnws_url = project.fdsnws_url

        if catalog_used and fdsnws_url:
            if any_model_runs_complete(forecast, session):
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
            msg = ("A seismic catalog has been added to "
                   "the forecast")
            fork_log(forecast, EStatus.RUNNING, msg, session, logger)
        elif not forecast.catalog:
            if project.seismiccatalog_required == EInput.OPTIONAL:
                msg = ("No seismic catalog will be attached to the "
                       "forecast")
                fork_log(forecast, EStatus.RUNNING, msg, session, logger)
            elif project.seismiccatalog_required == EInput.NOT_ALLOWED:
                msg = ("No seismic catalog allowed for forecast.")
                fork_log(forecast, EStatus.RUNNING, msg, session, logger)


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
            forecast.injectionwell = project.injectionwell
            session.commit()
            msg = ("Project has injectionwell, this will be used for the "
                   "forecast")
            fork_log(forecast, EStatus.RUNNING, msg, session, logger)
            return
        well_used = project.injectionwell_required in \
            [EInput.REQUIRED, EInput.OPTIONAL]

        if well_used and hydws_url:
            if any_model_runs_complete(forecast, session):
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
            msg = ("An Injection well has been added to "
                   "the forecast")
            fork_log(forecast, EStatus.RUNNING, msg, session, logger)
        elif not forecast.injectionwell:
            if project.injectionwell_required == EInput.OPTIONAL:
                logger.info("No observed well will be attached to the "
                            "forecast")
            elif project.injectionwell_required == EInput.NOT_ALLOWED:
                logger.info("No well allowed for forecast.")


@task(task_run_name="model_runs(forecast{forecast_id})")
def model_runs(
        forecast_id: int,
        connection_string: str) -> List[int]:
    with session_handler(connection_string) as session:
        forecast = get_forecast(forecast_id, session)
        model_run_ids = [r.id for r in forecast.runs if
                         r.status != EStatus.COMPLETED]
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
        model_config = model_run.modelconfig
        injection_plan = model_run.injectionplan
        forecast = model_run.forecast
        forecastseries = forecast.forecastseries

        payload = {
            'data': {
                "worker_config": {
                    "model_name": model_config.name,
                    "model_description": model_config.description,
                    "model_module": model_config.sfm_module,
                    "model_class": model_config.sfm_class},
                'attributes': {
                    'geometry': {
                        'bounding_polygon': forecastseries.boundingpolygon,
                        'altitude_min': forecastseries.altitudemin,
                        'altitude_max': forecastseries.altitudemax},
                    'seismic_catalog': forecast.seismiccatalog,
                    'injection_well': forecast.injectionwell,
                    'forecast_start': forecast.starttime,
                    'forecast_end': forecast.endtime,
                    'injection_plan': injection_plan,
                    'model_config': model_config.config}}}

        _worker_handle = RemoteSeismicityWorkerHandle(
            model_run.modelconfig.url)
        try:
            resp = _worker_handle.compute(
                payload,
                SFMWorkerIMessageSerializer(),
                SFMWorkerOMessageDeserializer(unknown=EXCLUDE))
            logger.info(f"response of seismicity worker: {resp}")
        except RemoteSeismicityWorkerHandle.RemoteWorkerError as err:
            msg = f"Remote worker error: {err}"
            fork_log(model_run, EStatus.FAILED, msg, session, logger)
        except RemoteSeismicityWorkerHandle.EncodingError as err:
            msg = f"Error encoding the payload: {err}"
            fork_log(model_run, EStatus.FAILED, msg, session, logger)
        else:
            status = resp['data']['attributes']['status_code']

            if status != TASK_ACCEPTED:
                msg = (f"model run {resp['data']['task_id']} "
                       f"has returned an error: {resp}")
                fork_log(model_run, EStatus.FAILED, msg, session, logger)

            else:
                model_run.runid = resp['data']['task_id']
                # Add commit here as above information is very important.
                session.commit()
                msg = (
                    f"model run is dispatched to {_worker_handle.url}. "
                    "Results will be polled at: "
                    f"{_worker_handle.url}/{model_run.runid}.")
                fork_log(model_run, EStatus.RUNNING, msg, session, logger)
        finally:
            return int(model_run.id)

@task(task_run_name="check_model_run_not_complete(model_run{model_run_id})") # noqa
def check_model_run_not_complete(
        model_run_id: int,
        connection_string: str) -> Optional[int]:
    with session_handler(connection_string) as session:
        logger = get_run_logger()
        model_run = get_model_run(model_run_id, session)
        if model_run.status == EStatus.RUNNING:
            return model_run_id
        elif model_run.status == EStatus.COMPLETED:
            logger.info("The model run is complete.")
        elif model_run.status == EStatus.FAILED:
            logger.info("The model run has a status of failed")
        else:
            logger.info("The model run has an unknown status: "
                        f"{model_run.status}")
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
        if any(model_run.status == EStatus.RUNNING
               for model_run in forecast.runs):
            logger.info(f"sleeping for {seconds_to_wait} seconds...")
            time.sleep(seconds_to_wait)
        else:
            pass

@task(task_run_name="check_model_runs_running(forecast_{forecast_id})") # noqa
def check_model_runs_running(
        forecast_id: int,
        connection_string: str) -> bool:
    with session_handler(connection_string) as session:
        logger = get_run_logger()
        logger.info(f"check model runs running forecast_id: {forecast_id}")
        forecast = get_forecast(forecast_id, session)
        all_statuses = [r.status for r in forecast.runs]
        logger.info(f"In checking models running, forecast: {forecast_id}, "
                    f"statuses: {all_statuses}")
        if EStatus.RUNNING in all_statuses:
            logger.debug("EStatus.RUNNING in all statuses")
            return True
        logger.debug("EStatus.RUNNING not in all statuses, quitting loop")
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
        if model_run.status in (
                EStatus.COMPLETED,
                EStatus.FAILED):
            logger.info("model run is complete or has errors, exiting")
            return
        msg = f"Polling for runid={model_run.runid}"
        fork_log(model_run, EStatus.RUNNING, msg, session,
                 logger, propagate=False)

        _worker_handle = RemoteSeismicityWorkerHandle(
            model_run.modelconfig.url)

        deserializer = SFMWorkerOMessageDeserializer(
            many=True)
        try:
            resp = _worker_handle.query(
                task_ids=model_run.runid,
                deserializer=deserializer).first()
        except RemoteSeismicityWorkerHandle.RemoteWorkerError as err:
            msg = f"Model run has got a worker error: {err}"
            fork_log(model_run, EStatus.FAILED, msg, session, logger)
            return Failed(message=err)
        except RemoteSeismicityWorkerHandle.HTTPError as err:
            msg = f"Model run has got a http error: {err}"
            fork_log(model_run, EStatus.FAILED, msg, session, logger)
            return Failed(message=err)
        else:
            status = resp['data']['attributes']['status_code']
            logger.info(f"status code of model run: {status}")

            if status in (TASK_ACCEPTED, TASK_PROCESSING):
                logger.info("status in accepted or processing")
                return

            logger.info(
                f'Received response (run={model_run!r}, '
                f'runid={model_run.runid}): {resp}')
            if status == TASK_COMPLETE:
                try:
                    result = resp['data']['attributes']['forecast']
                    model_run.resulttimebins = result
                    session.commit()
                    msg = "setting model run to complete"
                    fork_log(model_run, EStatus.COMPLETED,
                             msg, session, logger)
                    # After committing results, delete task from worker.
                    _worker_handle.delete(model_run.runid)
                    return
                except KeyError:
                    msg = (
                        "Remote Seismicity Worker has not returned "
                        f"a forecast (runid={model_run.runid}: "
                        f"{resp})")
                    fork_log(model_run, EStatus.FAILED, msg, session, logger)

                except RemoteSeismicityWorkerHandle.ConnectionError:
                    msg = ("A connection error to the worker means the data cannot be deleted in the worker database.")
                    fork_log(model_run, EStatus.COMPLETED, msg, session, logger)

                except Exception as err:
                    msg = (
                        "EXCEPTION! setting model run to finished "
                        f"with errors: {err}")
                    fork_log(model_run, EStatus.FAILED, msg, session, logger)

            elif status in TASK_ERROR:
                msg = (
                    "Remote Seismicity Model Worker"
                    " has returned an unsuccessful status code."
                    f"(runid={model_run.runid}: {resp})")
                fork_log(model_run, EStatus.FAILED, msg, session, logger)

            else:
                msg = (
                    "Remote Seismicity Model Worker"
                    " has returned an unhandled status code."
                    f"(runid={model_run.runid}: {resp})")
                fork_log(model_run, EStatus.FAILED, msg, session, logger)
