import json
import copy
from datetime import datetime
from typing import List

from prefect import task, get_run_logger
from prefect.tasks import exponential_backoff
from prefect.server.schemas.states import Failed
from ramsis.datamodel import EInput, EStage, EStatus, \
    Forecast, Project, SeismicObservationCatalog, InjectionWell
from ramsis.io.sfm import (SFMWorkerIMessageSerializer,
                           SFMWorkerOMessageDeserializer)

from RAMSIS.db import session_handler
from RAMSIS.core.datasources import FDSNWSDataSource, HYDWSDataSource
from RAMSIS.core.worker.sfm import RemoteSeismicityWorkerHandle
from RAMSIS.db_utils import get_forecast, get_scenario, \
    get_seismicity_model_run
from RAMSIS.error import ModelNotFinished, RemoteWorkerError


datetime_format = '%Y-%m-%dT%H:%M:%S.%f'


@task(task_run_name="run_seismicity_flow(forecast{forecast_id})")
def run_seismicity_flow(forecast_id: int, connection_string: str) -> bool:
    """
    If any of the scenarios have a seismicity stage that is not complete,
    return True.
    """
    with session_handler(connection_string) as session:
        logger = get_run_logger()
        forecast = get_forecast(forecast_id, session)
        for scenario in forecast.scenarios:
            if not scenario.enabled:
                continue
            seismicity_stage = scenario[EStage.SEISMICITY]
            if not seismicity_stage.enabled:
                continue
            elif seismicity_stage.status.state != EStatus.COMPLETE:
                logger.info("Seismicity Stage will be run.")
                seismicity_stage.status.state = EStatus.RUNNING
                session.commit()
                return True
        logger.info('Seismicity stage has been skipped'
                    f' for forecast_id: {forecast_id}'
                    ' as no tasks are required to be done.')
        return False


def some_model_runs_complete(
        forecast: Forecast) -> bool:
    """Return True if any enabled model runs are complete"""
    logger = get_run_logger()
    for scenario in forecast.scenarios:
        if not scenario.enabled:
            continue
        seismicity_stage = scenario[EStage.SEISMICITY]
        if not seismicity_stage.enabled:
            continue
        model_run_complete = any([r.id for r in seismicity_stage.runs if
                                  r.enabled and
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
    Update forecast scenarios and seismicity stage to running
    if enabled.
    """
    with session_handler(connection_string) as session:
        forecast = get_forecast(forecast_id, session)
        forecast.status.state = EStatus.RUNNING
        for scenario in forecast.scenarios:
            if scenario.enabled:
                scenario.status.state = EStatus.RUNNING
                seismicity_stage = scenario[EStage.SEISMICITY]
                seismicity_stage.status.state = EStatus.RUNNING
        session.commit()


@task(task_run_name="update_fdsn(forecast{forecast_id})")
def update_fdsn(forecast_id: int, dttime: datetime,
                connection_string: str) -> None:
    """
    Updates the catalog if the url is configured and
    a catalog is optional/required
    """
    def fetch_fdsn(url: str, project: Project,
                   forecast: Forecast) -> \
            SeismicObservationCatalog:
        logger = get_run_logger()
        logger.info("Fetch fdsn called")
        seismics_data_source = FDSNWSDataSource(
            url, timeout=None, project=project)
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
        project = forecast.project
        catalog_used = getattr(
            EInput, project.settings.config['seismic_catalog']) in \
            [EInput.REQUIRED, EInput.OPTIONAL]
        fdsnws_url = project.settings.config['fdsnws_url']
        logger.info(f"################fdsnws: {fdsnws_url}, {catalog_used}")

        if catalog_used and fdsnws_url:
            if some_model_runs_complete(forecast):
                logger.info("Some model runs are complete, therefore "
                             "no seismic catalog will be fetched.")
                return
            logger.info("A catalog is required and a url is specified: "
                        f"{fdsnws_url}")
            # Delete existing seismic catalog if it exsits, so that the most
            # up to date one is used
            if forecast.seismiccatalog:
                logger.debug("deleting existing seismic catalog on forecast")
                session.query(SeismicObservationCatalog).filter(
                    SeismicObservationCatalog.forecast_id == forecast_id).\
                    delete()
                session.commit()

            cat = fetch_fdsn(fdsnws_url, project, forecast)
            if not cat:
                cat = SeismicObservationCatalog()
                logger.warning(
                    "An empty catalog has been created as no "
                    "catalog has been returned from the FDSN web service.")
            else:
                logger.info(f"A catalog has been returned: {cat}")

            cat.creationinfo_creationtime = dttime
            forecast.seismiccatalog = [cat]
            session.add(cat)
            session.commit()
        elif catalog_used and forecast.seismiccatalog:
            logger.info("Forecast already has seismic catalog attached.")
        else:
            assert forecast.seismiccatalog and \
                len(forecast.seismiccatalog) > 0, \
                "No catalog exists on forecast"


@task(task_run_name="update_hyd(forecast{forecast_id})")
def update_hyd(forecast_id: int, dttime: datetime,
               connection_string: str) -> None:
    """
    Updates the hydraulic history if the url is configured and
    a hydraulics are optional/required
    """
    def fetch_hyd(url: str, project: Project,
                  forecast: Forecast) -> InjectionWell:
        logger = get_run_logger()
        logger.info("Fetch hydws called")
        hydraulics_data_source = HYDWSDataSource(
            url, timeout=None, project=project)
        hydraulics_data_source.enabled = True

        starttime = datetime.strftime(project.starttime, datetime_format)
        endtime = datetime.strftime(forecast.starttime, datetime_format)

        well = hydraulics_data_source.fetch(
            starttime=starttime,
            endtime=endtime,
            level='hydraulic')
        return well

    with session_handler(connection_string) as session:
        forecast = get_forecast(forecast_id, session)
        logger = get_run_logger()
        project = forecast.project
        well_requirement = getattr(
            EInput, project.settings.config['well'])
        hydws_url = project.settings.config['hydws_url']

        if hydws_url and well_requirement in [
                EInput.REQUIRED, EInput.OPTIONAL]:
            if some_model_runs_complete(forecast):
                logger.info("Some model runs are complete, therefore "
                             "no hydraulic data will be fetched.")    
                return
            if forecast.well:
                # Delete existing hydraulics if they exsit, so that the most
                # up to date data is used
                logger.debug("deleting existing well on forecast")
                session.query(InjectionWell).filter(
                    InjectionWell.forecast_id == forecast_id).delete()
                session.commit()
            logger.info("Well will be fetched for forecast.")
            well = fetch_hyd(hydws_url, project, forecast)
            assert hasattr(well, 'sections')
            well.creationinfo_creationtime = dttime
            forecast.well = [well]
            session.add(well)
            session.commit()
        elif forecast.well and well_requirement in [EInput.REQUIRED,
                                                    EInput.OPTIONAL]:
            logger.info("Forecast already has well attached.")
        elif not forecast.well:
            if well_requirement == EInput.OPTIONAL:
                logger.info("No observed well will be attached to the "
                            "forecast")
            elif well_requirement == EInput.NOT_ALLOWED:
                logger.info("No well allowed for forecast.")




@task(task_run_name="forecast_scenarios(forecast{forecast_id})")
def forecast_scenarios(forecast_id: int, connection_string: int) -> List[int]:
    with session_handler(connection_string) as session:
        forecast = get_forecast(forecast_id, session)
        scenario_ids = [s.id for s in forecast.scenarios if s.enabled]
    return scenario_ids


@task(task_run_name="model_runs(scenario{scenario_id})")
def model_runs(
        scenario_id: int,
        connection_string: str) -> List[int]:
    with session_handler(connection_string) as session:
        scenario = get_scenario(scenario_id, session)
        seismicity_stage = scenario[EStage.SEISMICITY]
        model_run_ids = [r.id for r in seismicity_stage.runs if r.enabled
                         and r.status.state != EStatus.COMPLETE]
    return model_run_ids

@task(task_run_name="forecast_serialize_data(forecast{forecast_id})")
def forecast_serialize_data(forecast_id: int, connection_string: int) -> dict:
    """
    :param str seismic_catalog: seismic catalog in
    `QuakeML <https://quake.ethz.ch/quakeml/QuakeML>` format
    :param well: injection well / borehole including
        the hydraulics.
    :type well: :py:class:`ramsis.datamodel.well.InjectionWell`
    :param scenario: The scenario to be forecasted
    :type scenario:
        :py:class:`ramsis.datamodel.hydraulics.InjectionPlan`
    :param str reservoir: Reservoir geometry in `WKT
        <https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry>`_
        format
    :param model_parameters: Model specific configuration parameters.
       If :code:`None` parameters are not appended.
    :type model_parameters: dict or None
    :param serializer: Serializer instance used to serialize the
        payload
    """
    with session_handler(connection_string) as session:
        forecast = get_forecast(forecast_id, session)
        project = forecast.project
        if forecast.well:
            well = forecast.well[0]
        else:
            well = None
        if forecast.seismiccatalog:
            seismiccatalog = forecast.seismiccatalog[0]
        else:
            seismiccatalog = None

        serializer = SFMWorkerIMessageSerializer(
            ramsis_proj=project.proj_string,
            external_proj="epsg:4326",
            ref_easting=0.0,
            ref_northing=0.0,
            transform_func_name='pyproj_transform_from_local_coords')
        payload = {
            'data': {
                'attributes': {
                    'seismicity': seismiccatalog,
                    'hydraulics': well,
                    'local_proj_string': project.proj_string}}}
        data = serializer._serialize_dict(payload)
        return data

@task(task_run_name="scenario_serialize_data(scenario{scenario_id})")
def scenario_serialize_data(
        scenario_id: int, connection_string: int) -> list:
    """
    :param str seismic_catalog: Snapshot of a seismic catalog in
    `QuakeML <https://quake.ethz.ch/quakeml/QuakeML>` format
    :param well: Snapshot of the injection well / borehole including
        the hydraulics.
    :type well: :py:class:`ramsis.datamodel.well.InjectionWell`
    :param scenario: The scenario to be forecasted
    :type scenario:
        :py:class:`ramsis.datamodel.hydraulics.InjectionPlan`
    :param str reservoir: Reservoir geometry in `WKT
        <https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry>`_
        format
    :param model_parameters: Model specific configuration parameters.
       If :code:`None` parameters are not appended.
    :type model_parameters: dict or None
    :param serializer: Serializer instance used to serialize the
        payload
    """
    with session_handler(connection_string) as session:
        scenario = get_scenario(scenario_id, session)
        forecast = scenario.forecast
        project = forecast.project
        injection_plan = scenario.well

        serializer = SFMWorkerIMessageSerializer(
            ramsis_proj=project.proj_string,
            external_proj="epsg:4326",
            ref_easting=0.0,
            ref_northing=0.0,
            transform_func_name='pyproj_transform_from_local_coords')

        seismicity_stage = scenario[EStage.SEISMICITY]
        model_run_ids = [r.id for r in seismicity_stage.runs if r.enabled
                         and r.status.state != EStatus.COMPLETE]

        payload = {
            'scenario_id': scenario_id,
            'data': {
                'attributes': {
                    'injection_plan': injection_plan,
                    'geometry': scenario.reservoirgeom}}}

        data = serializer._serialize_dict(payload)
        model_run_data_list = []
        for model_run_id in model_run_ids:
            model_run_payload = copy.deepcopy(payload)
            model_run_payload['model_run_id'] = model_run_id
            model_run_data_list.append(model_run_payload)
        return model_run_data_list

@task
def flatten_model_run_list(model_run_list: list) -> list:
    ret_list = []
    for sublist in model_run_list:
        for item in sublist:
            ret_list.append(item)
    return ret_list



@task(task_run_name="model_run_executor(forecast{forecast_id}_model_run)")
def model_run_executor(forecast_id: int, forecast_data: dict,
        model_run_data: dict, connection_string: str) -> int:
    """
    Executes a single seimicity model run

    The executor instantiates the actual model that is associated with the run,
    connects to its status update signal and then calls its run method.
    """
    TASK_ACCEPTED = 202

    with session_handler(connection_string) as session:
        model_run_id = model_run_data["model_run_id"]
        model_run = get_seismicity_model_run(model_run_id, session)
        logger = get_run_logger()
        model_run.status.state = EStatus.RUNNING
        session.commit()
        stage = model_run.forecaststage
        forecast = stage.scenario.forecast
        project = forecast.project

        _worker_handle = RemoteSeismicityWorkerHandle.from_run(
            model_run)
        config_attributes = {
            'forecast_start': forecast.starttime.isoformat(),
            'forecast_end': forecast.endtime.isoformat(),
            'epoch_duration': stage.config['epoch_duration'],
            'input_parameters': model_run.config}
        payload = {"data":
                   {"attributes":
                    {**config_attributes,
                     **forecast_data["data"]["attributes"],
                     **model_run_data["data"]["attributes"]}}}
        logger.info("The payload to seismicity models is of length: "
                    f"{len(payload)}")
        try:
            json_payload = json.dumps(payload)
            resp = _worker_handle.compute(
                json_payload,
                deserializer=SFMWorkerOMessageDeserializer(
                    ramsis_proj=project.proj_string,
                    external_proj="epsg:4326",
                    ref_easting=0.0,
                    ref_northing=0.0,
                    transform_func_name='pyproj_transform_to_local_coords')) # noqa
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
        return int(model_run.id)


@task(retries=1000,
      retry_delay_seconds=exponential_backoff(backoff_factor=1.5),
      retry_jitter_factor=1,
      task_run_name="poll_model_run(forecast{forecast_id}_model_run{model_run_id})")
def poll_model_run(forecast_id:int, model_run_id: int,
                   connection_string: int) -> None:
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
        model_run = get_seismicity_model_run(model_run_id, session)
        scenario = model_run.forecaststage.scenario
        stage = scenario[EStage.SEISMICITY]
        forecast = scenario.forecast
        logger = get_run_logger()
        logger.debug(f"Polling for runid={model_run.runid}")
        project = forecast.project

        _worker_handle = RemoteSeismicityWorkerHandle.from_run(
            model_run)

        deserializer = SFMWorkerOMessageDeserializer(
            ramsis_proj=project.proj_string,
            external_proj="epsg:4326",
            ref_easting=0.0,
            ref_northing=0.0,
            transform_func_name='pyproj_transform_to_local_coords',
            many=True)
        try:
            resp = _worker_handle.query(
                task_ids=model_run.runid,
                deserializer=deserializer).first()
        except RemoteSeismicityWorkerHandle.RemoteWorkerError as err:
            model_run.status.state = EStatus.ERROR
            return Failed(message=err)
        else:
            status = resp['data']['attributes']['status_code']
            logger.info(f"status code of model run: {status}")

            if status in (TASK_ACCEPTED, TASK_PROCESSING):
                logger.info("status in accepted or processing")
                raise ModelNotFinished(
                    f"(forecast{forecast.id})(scenario.id="
                    f"{model_run.forecaststage.scenario}) "
                    f"(runid={model_run.runid}): Polling")

            logger.info(
                f'Received response (run={model_run!r}, '
                f'runid={model_run.runid}): {resp}')
            if status == TASK_COMPLETE:
                try:
                    result = resp['data']['attributes']['forecast']
                except KeyError:
                    return Failed(message=
                        "Remote Seismicity Worker has not returned "
                        f"a forecast (runid={model_run.runid}: "
                        f"{resp})")
                else:
                    model_run.result = result
                    # session.add(result)
                    model_run.status.state = EStatus.COMPLETE
                    session.commit()

            elif status in TASK_ERROR:
                logger.info("status in error")
                model_run.status.state = EStatus.ERROR
                stage.status.state = EStatus.ERROR
                session.commit()
                logger.error("Remote Seismicity Model Worker"
                    " has returned an unsuccessful status code."
                    f"(runid={model_run.runid}: {resp})")

            else:
                model_run.status.state = EStatus.ERROR
                stage.status.state = EStatus.ERROR
                session.commit()
                logger.error(
                    "Remote Seismicity Model Worker"
                    " has returned an unhandled status code."
                    f"(runid={model_run.runid}: {resp})")
