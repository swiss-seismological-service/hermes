# Copyright (c) 2019, ETH Zurich, Swiss Seismological Service
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

import time
import copy
import logging
from prefect import task, Task
import prefect
from prefect.engine.signals import LOOP, FAIL
from prefect.engine.runner import ENDRUN
from prefect.engine.state import Skipped
from ramsis.datamodel.status import EStatus
from ramsis.datamodel.forecast import EStage

from RAMSIS.core.worker.sfm import RemoteSeismicityWorkerHandle
from RAMSIS.io.sfm import (SFMWorkerIMessageSerializer,
                           SFMWorkerOMessageDeserializer)
from RAMSIS.io.utils import (pymap3d_transform_geodetic2ned,
                             pymap3d_transform_ned2geodetic)
from RAMSIS.wkt_utils import point_to_proj4


log = logging.getLogger(__name__)


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
            skip = Skipped("skipping", result=forecast)
            raise ENDRUN(state=skip)
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
            # If a snapshot is already attached, skip task
            skip = Skipped("skipping", result=forecast)
            raise ENDRUN(state=skip)
        else:
            seismiccatalog = forecast.project.seismiccatalog.\
                snapshot(filter_cond=filter_future)

            assert(hasattr(seismiccatalog, 'events'))
            seismiccatalog.forecast_id = forecast.id
            seismiccatalog.creationinfo_creationtime = dttime
            forecast.seismiccatalog.append(seismiccatalog)
        return forecast


@task(skip_on_upstream_skip=False)
def forecast_scenarios(forecast):
    scenarios = [s for s in forecast.scenarios if s.enabled]
    return scenarios


class SeismicityModels(Task):
    def run(self, scenario):
        model_runs = []
        try:
            stage = scenario[EStage.SEISMICITY]
            stage_enabled = stage.enabled
        except KeyError:
            pass
        else:
            if stage_enabled:
                model_runs = [r for r in stage.runs if r.enabled]
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


class SeismicityModelRunExecutor(Task):
    """
    Executes a single seimicity model run

    The executor instantiates the actual model that is associated with the run,
    connects to its status update signal and then calls its run method.
    """
    TASK_ACCEPTED = 202

    def run(self, forecast, model_run):

        stage = model_run.forecaststage
        scenario = model_run.forecaststage.scenario
        project = forecast.project
        # (sarsonl) current bug when attempting to only
        # allow one to one relationship between forecast-well
        # and forecast-seismiccatalog. Work-around is to leave
        # as one to many relationship and assume just one item in list.
        well = forecast.well[0]
        injection_plan = scenario.well
        seismiccatalog = forecast.seismiccatalog[0]

        _worker_handle = RemoteSeismicityWorkerHandle.from_run(
            model_run)
        model_parameters = copy.deepcopy(model_run.config)
        model_parameters.update(
            {'datetime_start': forecast.starttime.isoformat(),
             'datetime_end': forecast.endtime.isoformat(),
             'epoch_duration': stage.config['prediction_bin_duration']})
        data = {
            'seismic_catalog': seismiccatalog,
            'well': well,
            'model_parameters': model_parameters,
            'reservoir': scenario.reservoirgeom,
            'scenario': {'well': injection_plan}, }

        serializer = SFMWorkerIMessageSerializer(
            proj=point_to_proj4(project.referencepoint),
            transform_callback=pymap3d_transform_ned2geodetic)
        payload = _worker_handle.Payload(**data, serializer=serializer)

        try:
            resp = _worker_handle.compute(
                payload, deserializer=SFMWorkerOMessageDeserializer())
        except RemoteSeismicityWorkerHandle.RemoteWorkerError:
            raise FAIL(message="model run submission has failed with error: "
                       "{err}", result=model_run)

        status = resp['data']['attributes']['status_code']

        if status != self.TASK_ACCEPTED:
            raise FAIL(message=f"model run {resp['data']['id']} "
                       f"has returned an error: {resp}", result=model_run)

        model_run.runid = resp['data']['id']
        return model_run


@task(skip_on_upstream_skip=False)
def dispatched_seismicity_model_runs(forecast):

    seismicity_stages = [s[EStage.SEISMICITY] for s in forecast.scenarios
                         if s.enabled]
    seismicity_stages = [stage for stage in seismicity_stages if stage.enabled]
    model_runs = []
    for stage in seismicity_stages:
        runs = stage.runs
        model_runs.extend([run for run in runs if run.runid and
                           run.status.state == EStatus.DISPATCHED])
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
            proj=point_to_proj4(project.referencepoint),
            transform_callback=pymap3d_transform_geodetic2ned,
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
                    model_run.result = result

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
