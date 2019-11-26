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
from prefect import task, Task, Flow
import prefect
from prefect.engine.signals import LOOP, SUCCESS, FAIL, RETRY, SKIP

from PyQt5.QtCore import pyqtSignal, QObject
from ramsis.datamodel.seismicity import SeismicityModelRun
from ramsis.datamodel.forecast import (Forecast, EStage,
                                       ForecastScenario,
                                       ForecastStage)
from sqlalchemy.orm import sessionmaker
from ramsis.datamodel.status import EStatus
from ramsis.utils.error import ErrorWithTraceback

from RAMSIS.core.tools.executor import (Executor, ParallelExecutor,
                                        SerialExecutor, ExecutionStatus,
                                        AbstractExecutor)
from RAMSIS.core.worker.sfm import RemoteSeismicityWorkerHandle
from RAMSIS.io.sfm import (SFMWorkerIMessageSerializer,
                           SFMWorkerOMessageDeserializer)
from RAMSIS.io.utils import (pymap3d_transform_geodetic2ned,
                             pymap3d_transform_ned2geodetic)
from RAMSIS.wkt_utils import point_to_proj4


log = logging.getLogger(__name__)


class ExecutorError(ErrorWithTraceback):
    """Base Executor error ({})."""

def forecast_state_handler(obj, old_state, new_state):
    msg = "\nTask state has changed from {0}:\n{1} to {2}\n"
    #obj.name = f"{obj.name}_altered"
    return new_state

def filter_future(event):
    return event.datetime_value < forecast.starttime

class DataSnapshot(Task):
    def run(self, forecast, dttime):
        def filter_future(event):
            return event.datetime_value < forecast.starttime

        self.forecast_starttime = forecast.starttime
        logger = prefect.context.get("logger")
        logger.info(f"In snapshot task with forecast.id: {forecast.id}")
        seismiccatalog = forecast.project.seismiccatalog.\
            snapshot(filter_cond=filter_future)
        seismiccatalog.forecast_id = forecast.id
        seismiccatalog.creationinfo_creationtime = dttime
        forecast.seismiccatalog_history.append(seismiccatalog)
        # XXX(damb): We only support one well with a single section at the
        # moment
        well = forecast.project.well.\
            snapshot(sample_filter_cond=filter_future)
        well.creationinfo_creationtime = dttime
        print('data snapshot', well.creationinfo_creationtime)
        well.forecast_id = forecast.id
        forecast.well_history.append(well)
        #forecast.scenario.well_history.append(well)
        print("securing the creationtime for well history: ", [i.creationinfo_creationtime for i in forecast.well_history])
        return forecast, well, seismiccatalog

@task
def data_snapshot(forecast):
    def filter_future(event):
        return event.datetime_value < forecast.starttime
    logger = prefect.context.get("logger")
    seismiccatalog = forecast.project.seismiccatalog.\
        snapshot(filter_cond=filter_future)
    seismiccatalog.forecast_id = forecast.id
    forecast.seismiccatalog_history.append(seismiccatalog)
    # XXX(damb): We only support one well with a single section at the
    # moment
    well = forecast.project.well.\
        snapshot(sample_filter_cond=filter_future)
    well.forecast_id = forecast.id
    forecast.well_history.append(well)
    return forecast

@task
def forecast_scenarios(forecast_data):
    forecast, _, _ = forecast_data
    print("forecast sceanrions the creationtime for well history: ", [i.creationinfo_creationtime for i in forecast.well_history])
    logger = prefect.context.get("logger")
    scenarios = [s for s in forecast.scenarios if s.enabled]
    return scenarios

class ForecastExecutor(Task):
    """
    Executes a forecast

    The `ForecastExecutor` executes a forecast by assemling all scenarios,
    stages and model runs Serial execution of scenarios

    :param RAMSIS.core.controller.Controller core: A reference to the core
    :param forecast: Forecast to execute
    :type forecast: ramsis.datamodel.forecast.ForecastScenario

    """
    #forecast_submitted = pyqtSignal(object)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.forecast_id = None
        self.status = ExecutionStatus(self, flag=ExecutionStatus.Flag.STARTED)
        prefect.context['forecast_id'] = None
        print("####in forecast executor, dir.. ", dir(prefect.context))

    def run(self, session, forecast_id):
        self.logger.info(f"Running forecast task for forecast_id: {forecast_id}")
        prefect.context['forecast_id'] = forecast_id
        self.forecast_id = forecast_id
        self.forecast = session.query(Forecast).\
            filter(Forecast.id == forecast_id).one_or_none()
        self.pre_process(session, self.forecast)
        scenario_ids = [s.id for s in self.forecast.scenarios if s.enabled]
        session.expunge(self.forecast)
        return scenario_ids
        

    def pre_process(self, session, forecast):
        """
        Prepares a forecast for running

        This includes associating the currently active welland taking a
        snapshot of the seismic catalog.

        :param Forecast forecast: Forecast to prepare
        :param datetime run_time: Time at which forecast is run

        """
        #log.info(f'Executing {self.objectName()}')
        #session.add(forecast)
        #session.add(forecast.project)

        # We may have future events in the live data if simulating
        def filter_future(event):
            return event.datetime_value < forecast.starttime

        seismiccatalog = forecast.project.seismiccatalog.\
            snapshot(filter_cond=filter_future)
        seismiccatalog.forecast_id = self.forecast.id
        forecast.seismiccatalog_history.append(seismiccatalog)
        # XXX(damb): We only support one well with a single section at the
        # moment
        well = forecast.project.well.\
            snapshot(sample_filter_cond=filter_future)
        well.forecast_id = self.forecast.id
        forecast.well_history.append(well)
        session.commit()
        #session.expunge(forecast)
        session.expunge(forecast.project)


class SeismicityForecastStageExecutor(Task):
    """
    Implements the seismicity forecast stage.

    Executes all seismicity forecast models for a specific scenario

    :param scenario: Scenario for which to execute model forecasts
    :type scenario: ramsis.datamodel.forecast.ForecastScenario
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scenario_id = None
        self.status = ExecutionStatus(self, flag=ExecutionStatus.Flag.STARTED)

    def run(self, session, scenario_id):
        self.scenario_id = scenario_id
        self.session = session
        model_run_ids = []
        #self.setObjectName(f'{stage_id!r}')
        self.scenario = session.query(ForecastScenario).\
            filter(ForecastScenario.id == scenario_id).one_or_none()
   
        try:
            # sarsonl: Will there only ever be one of each
            # stage type in a scenario?
            self.stage = self.scenario[EStage.SEISMICITY]
            stage_id = self.stage.id
            stage_enabled = self.stage.enabled
        except KeyError as err:
           pass 
        else:
            if stage_enabled:
                 model_run_ids = [r.id for r in self.stage.runs if r.enabled]
        self.session.expunge(self.scenario)
        return model_run_ids

@task
def seismicity_models(scenario):
    model_runs = []
    try:
        stage = scenario[EStage.SEISMICITY]
        stage_id = stage.id
        stage_enabled = stage.enabled
    except KeyError as err:
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
        #self.status_changed.emit(ExecutionStatus(self))
        pass

    def on_model_status_changed(self, notification):
        pass
        # model = self.sender()
        # self.proceed_on[0]execution_status = _create_execution_status(
        #       self, notification)
        # if notification.success:
        #     self.model_run.result = notification.result
        #
        # self.status_changed.emit(execution_status)


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
        #self.status_changed.emit(ExecutionStatus(self))
        pass

    def on_model_status_changed(self, notification):
        pass
        # model = self.sender()
        # execution_status = _create_execution_status(self, notification)
        # if notification.success:
        #     self.model_run.result = notification.result
        #
        # self.finished.emit(execution_status)


#class ScenarioStageExecutor(SerialExecutor):
#    """
#    Runs seismicity forecast, hazard and risk calculation for a scenario
#
#    :param scenario: Scenario for this job
#    :type scenario: ramsis.datamodel.forecast.ForecastScenario
#    """
#    _EXEC_MAP = {
#        EStage.SEISMICITY: SeismicityForecastStageExecutor,
#        EStage.HAZARD: HazardStageExecutor,
#        EStage.RISK: RiskStageExecutor, }
#
#    def run(self, session, scenario_id, stage_type):
#        self.scenario = session.query(ForecastScenario).\
#            filter(ForecastScenario.id == scenario_id).one_or_none()
#   
#       try:
#           stage = self.scenario[stage_type]
#           stage_id = stage.id
#           stage_enabled = stage.enabled
#           self.session.expunge(stage)
#       except KeyError as err:
#          pass 
#       else:
#           if stage_enabled:
#               stage_
#        for stage_type, executor in self._EXEC_MAP.items():
#            execute(stage_type, executor)
#        self.session.expunge(self.scenario)
#        return run_ids
#    def _setup(self):
#
#        def execute(stage_type, executor):
#            try:
#                stage = self.scenario[stage_type]
#                stage_id = stage.id
#                stage_enabled = stage.enabled
#                self.session.expunge(stage)
#            except KeyError as err:
#                raise ExecutorError(f'Missing stage: {err}')
#            else:
#                if stage_enabled:
#                    executor(stage_id, self.session, parent=self)
#
#        for stage_type, executor in self._EXEC_MAP.items():
#            execute(stage_type, executor)
#        self.session.expunge(self.scenario)
#
#    def pre_process(self):
#        log.info(f'Computing scenario: {self.scenario.name}')
#
#    def post_process(self):
#        log.info(f'Scenario {self.scenario.name!r} complete')
#

class SeismicityModelRunExecutor(Task):
    """
    Executes a single seimicity model run

    The executor instantiates the actual model that is associated with the run,
    connects to its status update signal and then calls its run method.
    """
    TASK_ACCEPTED = 202

    RESP_MAP = {
        TASK_ACCEPTED: (ExecutionStatus.Flag.STARTED, EStatus.PENDING),
        200: (ExecutionStatus.Flag.SUCCESS, EStatus.COMPLETE),
        423: (ExecutionStatus.Flag.RUNNING, EStatus.RUNNING),
        418: (ExecutionStatus.Flag.ERROR, EStatus.ERROR),
        204: (ExecutionStatus.Flag.ERROR, EStatus.ERROR),
        405: (ExecutionStatus.Flag.ERROR, EStatus.ERROR),
        422: (ExecutionStatus.Flag.ERROR, EStatus.ERROR),
        500: (ExecutionStatus.Flag.ERROR, EStatus.ERROR), }

    #def __init__(self, *args, **kwargs):
    #    super().__init__(*args, **kwargs)
    #    self.model_run_id = None

    def run(self, forecast_data, model_run=None):
        
        forecast, well, seismiccatalog = forecast_data
        print("forecast.well,sections", forecast.well.sections)
        print("model_run.forecaststage.scenario.well,sections", model_run.forecaststage.scenario.well.sections)
        logger = prefect.context.get('logger')
        stage = model_run.forecaststage
        scenario = model_run.forecaststage.scenario
        #forecast = model_run.forecaststage.scenario.forecast
        project = forecast.project
        #project = model_run.forecaststage.scenario.forecast.project

        _worker_handle = RemoteSeismicityWorkerHandle.from_run(
            model_run)
        model_parameters = copy.deepcopy(model_run.config)
        model_parameters.update(
            {'datetime_start': forecast.starttime.isoformat(),
             'datetime_end': forecast.endtime.isoformat(),
             'epoch_duration': stage.config['prediction_bin_duration']})
        data = {
            'seismic_catalog': forecast.seismiccatalog,
            'well': forecast.well,
            'model_parameters': model_parameters,
            'reservoir': scenario.reservoirgeom,
            'scenario': {'well': scenario.well}, }

        serializer = SFMWorkerIMessageSerializer(
            proj=point_to_proj4(project.referencepoint),
            transform_callback=pymap3d_transform_ned2geodetic)
        payload = _worker_handle.Payload(**data, serializer=serializer)

        try:
            resp = _worker_handle.compute(
                payload, deserializer=SFMWorkerOMessageDeserializer())
        except RemoteSeismicityWorkerHandle.RemoteWorkerError as err:
            log.error(str(err))
            raise FAIL(message="model run submission has failed with error: {err}")

        status = resp['data']['attributes']['status_code']

        if status != self.TASK_ACCEPTED:
            raise FAIL(message=f"model run {resp['data']['id']} has returned an error: {resp}")

        
        model_run.runid = resp['data']['id']
        print("resp from model worker: ", resp, type(resp))
        #raise SUCCESS(
        #    message=f"model run {resp['data']['id']}"
        #    f" has been submitted to the remote worker: {resp}")

        return model_run

@task
def dispatched_seismicity_model_runs(forecast_data):
    
    forecast, _, _ = forecast_data
    seismicity_stages = [s[EStage.SEISMICITY] for s in forecast.scenarios if s.enabled]
    seismicity_stages = [stage for stage in seismicity_stages if stage.enabled]
    #[item for sublist in l for item in sublist]
    model_runs = []
    for stage in seismicity_stages:
        runs = stage.runs
        model_runs.extend([run for run in runs if run.runid])
    #model_runs = [run for sublist in seismicity_stages for run in stage.runs]
    return model_runs


class SeismicityModelRunPoller(Task):
    """
    Executes a single seimicity model run

    The executor instantiates the actual model that is associated with the run,
    connects to its status update signal and then calls its run method.
    """
    TASK_ACCEPTED = 202

    STATUS = {'ACCEPTED': 1,
              'SUCCESS': 0}

    RESP_MAP = {
        TASK_ACCEPTED: (ExecutionStatus.Flag.STARTED, EStatus.PENDING),
        200: (ExecutionStatus.Flag.SUCCESS, EStatus.COMPLETE),
        423: (ExecutionStatus.Flag.RUNNING, EStatus.RUNNING),
        418: (ExecutionStatus.Flag.ERROR, EStatus.ERROR),
        204: (ExecutionStatus.Flag.ERROR, EStatus.ERROR),
        405: (ExecutionStatus.Flag.ERROR, EStatus.ERROR),
        422: (ExecutionStatus.Flag.ERROR, EStatus.ERROR),
        500: (ExecutionStatus.Flag.ERROR, EStatus.ERROR), }

    def run(self, forecast_data, model_run):
        """
        :param run: Model run to execute
        :type run: :py:class:`ramsis.datamodel.seismicity.SeismicityModelRun`
        """
        logger = prefect.context.get('logger')
        forecast, _, _ = forecast_data
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

            if status in (self.TASK_ACCEPTED, 423):
                time.sleep(15)
                raise LOOP()

            logger.info(f'Received response (run={model_run!r}, '
                     f'id={model_run.runid}): {resp}')
            if status == 200:
                # process result
                # TODO(damb): Perform this validation within the corresponding IO
                # facilities.
                try:
                    result = resp['data']['attributes']['forecast']
                except KeyError:
                    #self.model_run.status.state = EStatus.ERROR
                    status = ExecutionStatus(self, flag=ExecutionStatus.Flag.ERROR)
                    raise FAIL("Remote Seismicity Worker has not returned "
                            "a forecast (runid={}: {})".format(model_run.runid, resp))
                else:
                    model_run.result = result

                    return model_run, result
            else:
                raise FAIL(message="Remote Seismicity Model Worker"
                        " has returned an unsuccessful response. (runid={}: {})".\
                                format(model_run.runid, resp))

    def _update_orm_status(self, resp):
        return self.RESP_MAP[resp['data']['attributes']['status_code']][1]

    def _resp_to_status(self, resp):
        """
        Convert a SFM worker response into an :code:`ExecutionStatus`.

        :param dict resp: Response to convert
        """
        return ExecutionStatus(
            self, info=resp,
            flag=self.RESP_MAP[resp['data']['attributes']['status_code']][0])
