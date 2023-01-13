# Copyright (c) 2019, ETH Zurich, Swiss Seismological Service # Noqa
"""
Classes to execute a forecast

A forecast is a sequence of serial and parallel scenarios, stages and model
runs. We use the Executor framework to implement this sequence, i.e. each
stage is managed by a respective StageExecutor class:

.. code-block: none
   Forecast                     Executes a forecast by computing all forecast
                                  scenarios sequentially.
     ForecastScenario           Executes a single scenario by computing all
                                  stages sequentially
       SeismicityForecastStage  Runs the induced seismicity models, parallel
         SeismicityModelRun     Runs a single induced seismicity model
         SeismicityModelRun
         ...
       HazardForecastStage      Runs the hazard stage of a forecast
       RiskForecastStage        Runs the risk stage of a forecast
     ForecastScenario
     ...

"""
import json
import time
from datetime import datetime

import prefect
from prefect import Task, task
from prefect.engine.signals import FAIL, LOOP
from prefect.triggers import any_successful
from ramsis.datamodel import EInput, EStage, EStatus
from ramsis.io.sfm import (SFMWorkerIMessageSerializer,
                           SFMWorkerOMessageDeserializer)

from RAMSIS.core.datasources import FDSNWSDataSource, HYDWSDataSource
from RAMSIS.core.worker.sfm import RemoteSeismicityWorkerHandle
from RAMSIS.core.engine import scenario_context_format, \
    model_run_context_format


datetime_format = '%Y-%m-%dT%H:%M:%S.%f'


class DummyTask(Task):
    """Dummy task to allow action to be taken
    on forecast with state handler.
    """
    def run(self, forecast):
        return forecast


class UpdateFdsn(Task):
    def fetch_fdsn(self, url, project, forecast):
        """
        FDSN task function
        """
        logger = prefect.context.get('logger')
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

    def run(self, forecast, dttime):
        # Additional logging context
        logger = prefect.context.get('logger')
        project = forecast.project
        catalog_used = getattr(
            EInput, project.settings.config['seismic_catalog']) in \
            [EInput.REQUIRED, EInput.OPTIONAL]
        fdsnws_url = project.settings.config['fdsnws_url']

        if catalog_used and fdsnws_url:
            logger.info("A catalog is required and a url is specified: "
                        f"{fdsnws_url}")
            cat = self.fetch_fdsn(fdsnws_url, project, forecast)
            cat.forecast_id = forecast.id
            cat.creationinfo_creationtime = dttime
            forecast.seismiccatalog = [cat]
        elif catalog_used and forecast.seismiccatalog:
            logger.info("Forecast already has seismic catalog attached.")
        else:
            assert forecast.seismiccatalog and \
                len(forecast.seismiccatalog) > 0, \
                "No catalog exists on forecast"
        return forecast


class UpdateHyd(Task):

    def fetch_hyd(self, url, project, forecast):
        """
        HYDWS task function
        """
        logger = prefect.context.get('logger')
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

    def run(self, forecast, dttime):
        logger = prefect.context.get('logger')
        project = forecast.project
        well_requirement = getattr(
            EInput, project.settings.config['well'])
        hydws_url = project.settings.config['hydws_url']

        if hydws_url and well_requirement in [
                EInput.REQUIRED, EInput.OPTIONAL]:
            logger.info("Well will be fetched for forecast.")
            well = self.fetch_hyd(hydws_url, project, forecast)
            assert hasattr(well, 'sections')
            well.creationinfo_creationtime = dttime
            well.forecast_id = forecast.id
            forecast.well = [well]
        elif forecast.well and well_requirement in [EInput.REQUIRED,
                                                    EInput.OPTIONAL]:
            logger.info("Forecast already has well attached.")
        elif not forecast.well:
            if well_requirement == EInput.OPTIONAL:
                logger.info("No observed well will be attached to the "
                            "forecast")
            elif well_requirement == EInput.NOT_ALLOWED:
                logger.info("No well allowed for forecast.")
        return forecast


@task
def skip_seismicity_stage(forecast):
    logger = prefect.context.get('logger')
    logger.info('Seismicity stage has been skipped'
                f' for forecast_id: {forecast.id}'
                ' as no tasks are required to be done.')


@task
def seismicity_stage_complete(forecast):

    status_work_required = [
        EStatus.DISPATCHED,
        EStatus.PENDING]

    seismicity_stage_done = True
    for scenario in forecast.scenarios:
        try:
            stage = scenario[EStage.SEISMICITY]
            stage_enabled = stage.enabled
        except KeyError:
            continue
        else:
            if stage_enabled:
                for r in stage.runs:
                    if r.status.state in status_work_required:
                        seismicity_stage_done = False
                        continue
        return seismicity_stage_done


class FlattenTask(Task):
    def run(self, nested_list):
        flattened_list = [item for sublist in nested_list for item in sublist]
        print("flattened$$$$$$$$$$$", flattened_list)
        return flattened_list


@task
def check_stage_enabled(scenario, estage):
    try:
        stage_enabled = scenario[estage].enabled
    except (KeyError, AttributeError):
        stage_enabled = False
    return stage_enabled


@task
def forecast_scenarios(forecast):
    scenarios = [s for s in forecast.scenarios if s.enabled]
    return scenarios


class ModelRuns(Task):
    # model_run status should have been set to RUNNING
    # but as long as is is not already DISPATCHED (sent to
    # remote worker and need to get response) COMPLETED
    # (already successfully run) or ERROR (many types of error
    # are included), the model_run is allowed to
    # rerun.
    STATUS_POSTED = [EStatus.DISPATCHED,
                     EStatus.COMPLETE]

    def run(self, scenario, stage_type):
        model_runs = []
        try:
            stage = scenario[stage_type]
            stage_enabled = stage.enabled
        except KeyError:
            pass
        else:
            if stage_enabled:
                model_runs = [r for r in stage.runs if r.enabled and
                              r.status.state not in self.STATUS_POSTED]
        return model_runs


class ForecastSerializeData(Task):
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
    def run(self, forecast):
        # Deepcopy items that are transformed, otherwise
        # due to concurrency, the same object gets transformed
        # multiple times.
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


class ScenarioSerializeData(Task):
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
    def run(self, scenario):
        context_str = scenario_context_format.format(
            forecast_id=scenario.forecast.id,
            scenario_id=scenario.id)
        with prefect.context(forecast_context=context_str):
            # Deepcopy items that are transformed, otherwise
            # due to concurrency, the same object gets transformed
            # multiple times.
            forecast = scenario.forecast
            project = forecast.project
            injection_plan = scenario.well

            serializer = SFMWorkerIMessageSerializer(
                ramsis_proj=project.proj_string,
                external_proj="epsg:4326",
                ref_easting=0.0,
                ref_northing=0.0,
                transform_func_name='pyproj_transform_from_local_coords')
            payload = {
                'data': {
                    'attributes': {
                        'injection_plan': injection_plan,
                        'geometry': scenario.reservoirgeom}}}

            data = serializer._serialize_dict(payload)
            return (scenario.id, data)


class SeismicityModelRunExecutor(Task):
    """
    Executes a single seimicity model run

    The executor instantiates the actual model that is associated with the run,
    connects to its status update signal and then calls its run method.
    """
    TASK_ACCEPTED = 202

    def run(self, forecast, forecast_data, scenario_data_list, model_run):
        context_str = model_run_context_format.format(
            forecast_id=forecast.id,
            scenario_id=model_run.forecaststage.scenario.id,
            model_run_id=model_run.id)
        with prefect.context(forecast_context=context_str):
            # Deepcopy items that are transformed, otherwise
            # due to concurrency, the same object gets transformed
            # multiple times.
            stage = model_run.forecaststage
            project = forecast.project
            scenario_data = [data for scenario_id, data
                             in scenario_data_list if
                             scenario_id ==
                             model_run.forecaststage.scenario.id][0]
            # (sarsonl) current bug when attempting to only
            # allow one to one relationship between forecast-well
            # and forecast-seismiccatalog. Work-around is to leave
            # as one to many relationship and assume just one item in list.

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
                         **scenario_data["data"]["attributes"]}}}
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
            except RemoteSeismicityWorkerHandle.RemoteWorkerError:
                raise FAIL(
                    message="model run submission has failed with "
                    "error: RemoteWorkerError. Check if remote worker is"
                    " accepting requests.",
                    result=model_run)

            status = resp['data']['attributes']['status_code']

            if status != self.TASK_ACCEPTED:
                raise FAIL(message=f"model run {resp['data']['task_id']} "
                           f"has returned an error: {resp}", result=model_run)

            model_run.runid = resp['data']['task_id']
            # Next task requires knowledge of status, so update status
            # inside task.
            model_run.status.state = EStatus.DISPATCHED
            return model_run


@task(trigger=any_successful)
def dispatched_model_runs(forecast, estage):
    logger = prefect.context.get('logger')
    stages = [s[estage] for s in forecast.scenarios
              if s.enabled]
    stages = [stage for stage in stages if stage.enabled]
    model_runs = []
    for stage in stages:
        runs = [r for r in stage.runs if r.id]
        # If not all the runs have been set to DISPATCHED, they are still
        # in a RUNNING state, which is changed by the state handler. However
        # this may not happen quickly enough to update here.
        model_runs.extend([run for run in runs if run.runid and
                           run.status.state == EStatus.DISPATCHED])

    logger.info(f'Returning model runs from dispatched task, {model_runs}')
    return model_runs


class SeismicityModelRunPoller(Task):
    """
    Executes a single seimicity model run

    The executor instantiates the actual model that is associated with the run,
    connects to its status update signal and then calls its run method.
    """
    TASK_ACCEPTED = 202
    TASK_PROCESSING = 423
    TASK_COMPLETE = 200
    TASK_ERROR = [418, 204, 405, 422, 500]

    def run(self, forecast, model_run):
        """
        :param run: Model run to execute
        :type run: :py:class:`ramsis.datamodel.seismicity.SeismicityModelRun`
        """
        context_str = model_run_context_format.format(
            forecast_id=forecast.id,
            scenario_id=model_run.forecaststage.scenario.id,
            model_run_id=model_run.id)
        with prefect.context(forecast_context=context_str):
            logger = prefect.context.get('logger')
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
                logger.error(str(err))
                model_run.status.state = EStatus.ERROR
                raise FAIL()
            else:
                status = resp['data']['attributes']['status_code']

                if status in (self.TASK_ACCEPTED, self.TASK_PROCESSING):
                    logger.info("sleeping")
                    time.sleep(15)
                    raise LOOP(
                        message=f"(forecast{forecast.id})(scenario.id="
                        f"{model_run.forecaststage.scenario}) "
                        f"(runid={model_run.runid}): Polling")

                logger.info(
                    f'Received response (run={model_run!r}, '
                    f'runid={model_run.runid}): {resp}')
                if status == self.TASK_COMPLETE:
                    try:
                        result = resp['data']['attributes']['forecast']
                    except KeyError:
                        raise FAIL("Remote Seismicity Worker has not returned "
                                   f"a forecast (runid={model_run.runid}: "
                                   f"{resp})",
                                   result=model_run)
                    else:
                        model_run.status.state = EStatus.COMPLETE
                        return model_run, result

                elif status in self.TASK_ERROR:
                    model_run.status.state = EStatus.ERROR
                    raise FAIL(
                        message="Remote Seismicity Model Worker"
                        " has returned an unsuccessful status code."
                        f"(runid={model_run.runid}: {resp})", result=model_run)

                else:
                    model_run.status.state = EStatus.ERROR
                    raise FAIL(
                        message="Remote Seismicity Model Worker"
                        " has returned an unhandled status code."
                        f"(runid={model_run.runid}: {resp})", result=model_run)
