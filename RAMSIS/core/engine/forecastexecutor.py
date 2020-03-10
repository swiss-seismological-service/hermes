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
import copy
import logging
from sqlalchemy import inspect
from prefect import task, Task
import prefect
from prefect.engine.signals import LOOP, FAIL
from ramsis.datamodel.status import EStatus
from ramsis.datamodel.forecast import EStage

from RAMSIS.core.worker.sfm import RemoteSeismicityWorkerHandle
from RAMSIS.io.sfm import (SFMWorkerIMessageSerializer,
                           SFMWorkerOMessageDeserializer)

log = logging.getLogger(__name__)


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
        return flattened_list


@task
def check_stage_enabled(scenario, estage):
    try:
        stage_enabled = scenario[estage].enabled
    except (KeyError, AttributeError):
        stage_enabled = False
    return stage_enabled


class WellSnapshot(Task):
    """
    Prefect task to attach snapshot in time of the
    hydraulic well to a forecast.
    """
    def run(self, forecast, dttime):
        """
        Returns updated forecast with new snapshot of well.
        If a well is already associated with the forecast,
        the task is skipped.
        """
        def filter_future(event):
            return event.datetime_value < forecast.starttime

        if forecast.well:
            # If a snapshot is already attached, skip task
            # (sarsonl) bug in prefect meaning that raise SKIP
            # cannot be used, this is the work-around.
            pass
        else:
            well = forecast.project.well.\
                snapshot(sample_filter_cond=filter_future)

            assert(hasattr(well, 'sections'))
            well.creationinfo_creationtime = dttime
            well.forecast_id = forecast.id
            forecast.well.append(well)
        return forecast


class CatalogSnapshot(Task):
    """
    Prefect task to attach snapshot in time of the
    hydraulic well to a forecast.
    """
    def run(self, forecast, dttime):
        """
        Returns updated forecast with new snapshot of catalog.
        If a catalog is already associated with the forecast,
        the task is skipped.
        """
        def filter_future(event):
            return event.datetime_value < forecast.starttime

        if forecast.seismiccatalog:
            pass
        else:
            seismiccatalog = forecast.project.seismiccatalog.\
                snapshot(filter_cond=filter_future)

            assert(hasattr(seismiccatalog, 'events'))
            seismiccatalog.forecast_id = forecast.id
            seismiccatalog.creationinfo_creationtime = dttime
            forecast.seismiccatalog.append(seismiccatalog)
        return forecast


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
                     EStatus.COMPLETE,
                     EStatus.ERROR]

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


class HazardStageExecutor(Task):
    """
    Executes the hazard stage

    The executor instantiates the OQ hazard client, connects to its status
    update signal and then calls its run method.

    :param scenario: Scenario for which to compute the hazard
    :type scenario: ramsis.datamodel.forecast.ForecastScenario
    """
    # TODO: this is mostly just pseudo-code since the interface will change
    #   completely with OQ 3 and the new client/worker classes. Re-add as soon
    #   as we have the new hazard (OQ) client implementation.

    def run(self):
        # TODO LH: implement
        # self.model_run.model.run()
        # TODO LH: remove, fake instant success for testing :)
        pass

    def on_model_status_changed(self, notification):
        pass
        # model = self.sender()
        # self.proceed_on[0]execution_status = _create_execution_status(
        #       self, notification)
        # if notification.success:
        #     self.model_run.result = notification.result
        #


class RiskStageExecutor(Task):
    """
    Executes the risk stage

    The executor instantiates the OQ risk client, connects to its status
    update signal and then calls its run method.

    :param scenario: Scenario for which to compute the hazard
    :type scenario: ramsis.datamodel.forecast.ForecastScenario
    """
    # TODO: this is mostly just pseudo-code since the interface will change
    #   completely with OQ 3 and the new client/worker classes. Re-add as soon
    #   as we have the new hazard (OQ) client implementation.

    def run(self):
        # TODO LH: implement
        # self.model_run.model.run()
        # TODO LH: remove, fake instant success for testing :)
        pass

    def on_model_status_changed(self, notification):
        pass
        # model = self.sender()
        # execution_status = _create_execution_status(self, notification)
        # if notification.success:
        #     self.model_run.result = notification.result
        #

class ForecastSerializeData(Task):
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
    def run(self, forecast):
        # Deepcopy items that are transformed, otherwise
        # due to concurrency, the same object gets transformed
        # multiple times.
        project = forecast.project
        well = forecast.well[0]
        seismiccatalog = forecast.seismiccatalog[0]

        serializer = SFMWorkerIMessageSerializer(
            ramsis_proj=project.spatialreference,
            external_proj="epsg:4326",
            ref_easting=project.referencepoint_x,
            ref_northing=project.referencepoint_y,
            transform_func_name='pyproj_transform_from_local_coords')
        payload = {
            'data': {
                'attributes': {
                    'seismic_catalog': {'quakeml': seismiccatalog},
                    'well': well,
                    'spatialreference': project.spatialreference,
                    'referencepoint': {
                        'x': project.referencepoint_x,
                        'y': project.referencepoint_y},
                    }}}

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
        # Deepcopy items that are transformed, otherwise
        # due to concurrency, the same object gets transformed
        # multiple times.
        forecast = scenario.forecast
        project = forecast.project
        injection_plan = scenario.well

        serializer = SFMWorkerIMessageSerializer(
            ramsis_proj=project.spatialreference,
            external_proj="epsg:4326",
            ref_easting=project.referencepoint_x,
            ref_northing=project.referencepoint_y,
            transform_func_name='pyproj_transform_from_local_coords')
        payload = {
            'data': {
                'attributes': {
                    'scenario': {'well': injection_plan},
                    'reservoir': {'geom': scenario.reservoirgeom}}}}

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
        # Deepcopy items that are transformed, otherwise
        # due to concurrency, the same object gets transformed
        # multiple times.
        stage = model_run.forecaststage
        scenario = model_run.forecaststage.scenario
        project = forecast.project
        scenario_data = [data for scenario_id, data in scenario_data_list if scenario_id == model_run.forecaststage.scenario.id][0]
        # (sarsonl) current bug when attempting to only
        # allow one to one relationship between forecast-well
        # and forecast-seismiccatalog. Work-around is to leave
        # as one to many relationship and assume just one item in list.

        _worker_handle = RemoteSeismicityWorkerHandle.from_run(
            model_run)
        model_parameters = copy.deepcopy(model_run.config)
        model_parameters.update(
            {'datetime_start': forecast.starttime.isoformat(),
             'datetime_end': forecast.endtime.isoformat(),
             'epoch_duration': stage.config['prediction_bin_duration']})
        payload = forecast_data
        attributes = payload["data"]["attributes"]
        scenario_attributes = scenario_data["data"]["attributes"]
        attributes["model_parameters"] = model_parameters
        attributes["reservoir"] = scenario_attributes["reservoir"]
        attributes["scenario"] = scenario_attributes["scenario"]

        try:
            resp = _worker_handle.compute(
                json.dumps(payload), deserializer=SFMWorkerOMessageDeserializer(
                    ramsis_proj=project.spatialreference,
                    external_proj="epsg:4326",
                    ref_easting=project.referencepoint_x,
                    ref_northing=project.referencepoint_y,
                    transform_func_name='pyproj_transform_to_local_coords'))
        except RemoteSeismicityWorkerHandle.RemoteWorkerError:
            raise FAIL(
                message="model run submission has failed with "
                "error: RemoteWorkerError. Check if remote worker is"
                " accepting requests.",
                result=model_run)

        status = resp['data']['attributes']['status_code']

        if status != self.TASK_ACCEPTED:
            raise FAIL(message=f"model run {resp['data']['id']} "
                       f"has returned an error: {resp}", result=model_run)

        model_run.runid = resp['data']['id']
        # Next task requires knowledge of status, so update status inside task.
        model_run.status.state = EStatus.DISPATCHED
        return model_run


@task
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
        logger = prefect.context.get('logger')
        logger.debug(f"Polling for runid={model_run.runid}")
        project = forecast.project

        _worker_handle = RemoteSeismicityWorkerHandle.from_run(
            model_run)

        deserializer = SFMWorkerOMessageDeserializer(
            ramsis_proj=project.spatialreference,
            external_proj="epsg:4326",
            ref_easting=project.referencepoint_x,
            ref_northing=project.referencepoint_y,
            transform_func_name='pyproj_transform_to_local_coords',
            many=True)
        try:
            resp = _worker_handle.query(
                task_ids=model_run.runid,
                deserializer=deserializer).first()
        except RemoteSeismicityWorkerHandle.RemoteWorkerError as err:
            logger.error(str(err))
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
                               f"a forecast (runid={model_run.runid}: {resp})",
                               result=model_run)
                else:
                    #model_run.result = result
                    return model_run, result

            elif status in self.TASK_ERROR:
                raise FAIL(
                    message="Remote Seismicity Model Worker"
                    " has returned an unsuccessful status code."
                    f"(runid={model_run.runid}: {resp})", result=model_run)

            else:
                raise FAIL(
                    message="Remote Seismicity Model Worker"
                    " has returned an unhandled status code."
                    f"(runid={model_run.runid}: {resp})", result=model_run)
