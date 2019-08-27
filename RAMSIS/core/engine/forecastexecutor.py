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

import copy
import logging

from PyQt5.QtCore import QTimer

from ramsis.datamodel.forecast import EStage
from ramsis.utils.error import ErrorWithTraceback

from RAMSIS.core.tools.executor import (Executor, ParallelExecutor,
                                        SerialExecutor, ExecutionStatus)
from RAMSIS.core.worker.sfm import RemoteSeismicityWorkerHandle
from RAMSIS.io.sfm import (SFMWorkerIMessageSerializer,
                           SFMWorkerOMessageDeserializer)
from RAMSIS.io.utils import (pymap3d_transform_geodetic2ned,
                             pymap3d_transform_ned2geodetic)
from RAMSIS.wkt_utils import point_to_proj4


log = logging.getLogger(__name__)


# NOTE(damb): Due to the hierarchical architecture of the pipeline
# implementation below it seemed easier to pass top-level objects to *executor
# constructors. Clients can exctract what's required to execute their task.
# Though, this approach contradicts encapsulation taught by OOP (I'm sorry - it
# wasn't me!).


class ExecutorError(ErrorWithTraceback):
    """Base Executor error ({})."""


class ForecastExecutor(SerialExecutor):
    """
    Executes a forecast

    The `ForecastExecutor` executes a forecast by assemling all scenarios,
    stages and model runs Serial execution of scenarios

    :param RAMSIS.core.controller.Controller core: A reference to the core
    :param forecast: Forecast to execute
    :type forecast: ramsis.datamodel.forecast.ForecastScenario

    """

    def __init__(self, core, forecast, **kwargs):
        super().__init__(**kwargs)
        self.setObjectName(f'{forecast!r}')
        self.core = core
        self.forecast = forecast
        for scenario in forecast.scenarios:
            if scenario.enabled:
                ScenarioExecutor(scenario, parent=self)

    def pre_process(self):
        """
        Prepares a forecast for running

        This includes associating the currently active welland taking a
        snapshot of the seismic catalog.

        :param Forecast forecast: Forecast to prepare
        :param datetime run_time: Time at which forecast is run

        """
        log.info(f'Executing {self.objectName()}')

        # We may have future events in the live data if simulating
        def filter_future(event):
            return event.datetime_value < self.forecast.starttime

        self.forecast.seismiccatalog = self.core.project.seismiccatalog.\
            snapshot(filter_cond=filter_future)

        # XXX(damb): We only support one well with a single section at the
        # moment
        self.forecast.well = self.core.project.wells[0].\
            snapshot(sample_filter_cond=filter_future)

        self.core.store.save()

    def post_process(self):
        self.core.store.save()
        log.info('Forecast {} completed'.format(self.forecast.starttime))

    def on_child_status_changed(self, status):
        # Do a save whenever intermediate results become available. It's the
        # childrens responsibility to add their respective results to the
        # scenario before the save takes place.
        self.core.store.save()
        super().on_child_status_changed(status)


class SeismicityForecastStageExecutor(ParallelExecutor):
    """
    Implements the seismicity forecast stage.

    Executes all seismicity forecast models for a specific scenario

    :param scenario: Scenario for which to execute model forecasts
    :type scenario: ramsis.datamodel.forecast.ForecastScenario
    """

    def __init__(self, stage, **kwargs):
        super().__init__(**kwargs)
        self.setObjectName(f'{stage!r}')
        self.stage = stage
        self.scenario = stage.scenario
        self.forecast = stage.scenario.forecast

        for model_run in self.stage.runs:
            if model_run.enabled:
                SeismicityModelRunExecutor(model_run, parent=self)

    def pre_process(self):
        log.info(f'Starting seismicity forecast stage for scenario '
                 f'"{self.objectName()}"')

    def post_process(self):
        log.info(f'All seismicity forecast models complete for scenario '
                 f'"{self.objectName()}"')


class HazardStageExecutor(Executor):
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

    def __init__(self, stage, **kwargs):
        super().__init__(**kwargs)
        self.setObjectName(f'{stage!r}')
        # stage = next(s for s in scenario.stages
        #                   if isinstance(s, HazardForecastStage))
        # self.model_run = stage.run
        # self.model_run.model.status_changed.connect(
        #     self.on_model_status_changed)

    def run(self):
        # TODO LH: implement
        # self.model_run.model.run()
        # TODO LH: remove, fake instant success for testing :)
        self.status_changed.emit(ExecutionStatus(self))

    def on_model_status_changed(self, notification):
        pass
        # model = self.sender()
        # execution_status = _create_execution_status(self, notification)
        # if notification.success:
        #     self.model_run.result = notification.result
        #
        # self.status_changed.emit(execution_status)


class RiskStageExecutor(Executor):
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

    def __init__(self, stage, **kwargs):
        super().__init__(**kwargs)
        self.setObjectName(f'{stage!r}')
        # stage = next(s for s in scenario.stages
        #                   if isinstance(s, RiskForecastStage))
        # self.model_run = stage.run
        # self.model_run.model.status_changed.connect(
        #     self.on_model_status_changed)

    def run(self):
        # TODO LH: implement
        # self.model_run.model.run()
        # TODO LH: remove, fake instant success for testing :)
        self.status_changed.emit(ExecutionStatus(self))

    def on_model_status_changed(self, notification):
        pass
        # model = self.sender()
        # execution_status = _create_execution_status(self, notification)
        # if notification.success:
        #     self.model_run.result = notification.result
        #
        # self.finished.emit(execution_status)


class ScenarioExecutor(SerialExecutor):
    """
    Runs seismicity forecast, hazard and risk calculation for a scenario

    :param scenario: Scenario for this job
    :type scenario: ramsis.datamodel.forecast.ForecastScenario
    """
    _EXEC_MAP = {
        EStage.SEISMICITY: SeismicityForecastStageExecutor,
        EStage.HAZARD: HazardStageExecutor,
        EStage.RISK: RiskStageExecutor, }

    def __init__(self, scenario, **kwargs):
        super().__init__(**kwargs)
        self.setObjectName(f'{scenario!r}')
        self.scenario = scenario
        self.forecast = scenario.forecast

        self._run()

    def _run(self):

        def execute(stage_type, executor):
            try:
                stage = self.scenario[stage_type]
            except KeyError as err:
                raise ExecutorError(f'Missing stage: {err}')
            else:
                if stage.enabled:
                    executor(stage, parent=self)

        for stage_type, executor in self._EXEC_MAP.items():
            execute(stage_type, executor)

    def pre_process(self):
        log.info(f'Computing scenario: {self.scenario.name}')

    def post_process(self):
        log.info(f'Scenario {self.scenario.name!r} complete')


class SeismicityModelRunExecutor(Executor):
    """
    Executes a single seimicity model run

    The executor instantiates the actual model that is associated with the run,
    connects to its status update signal and then calls its run method.
    """
    POLLING_INTERVAL = 5000
    TASK_ACCEPTED = 202

    RESP_MAP = {
        TASK_ACCEPTED: ExecutionStatus.Flag.STARTED,
        200: ExecutionStatus.Flag.SUCCESS,
        423: ExecutionStatus.Flag.RUNNING,
        418: ExecutionStatus.Flag.ERROR,
        204: ExecutionStatus.Flag.ERROR,
        405: ExecutionStatus.Flag.ERROR,
        422: ExecutionStatus.Flag.ERROR,
        500: ExecutionStatus.Flag.ERROR, }

    def __init__(self, model_run, **kwargs):
        """
        :param run: Model run to execute
        :type run: :py:class:`ramsis.datamodel.seismicity.SeismicityModelRun`
        """
        super().__init__(**kwargs)
        self.setObjectName(f'{model_run!r}')

        self.model_run = model_run
        self.stage = model_run.forecaststage
        self.scenario = model_run.forecaststage.scenario
        self.forecast = model_run.forecaststage.scenario.forecast
        self.project = model_run.forecaststage.scenario.forecast.project

        self._worker_handle = RemoteSeismicityWorkerHandle.from_run(
            self.model_run)

    def run(self):
        log.info(f'Running seismicity forecast model {self.objectName()}')

        model_parameters = copy.deepcopy(self.model_run.config)
        model_parameters.update(
            {'datetime_start': self.forecast.starttime.isoformat(),
             'datetime_end': self.forecast.endtime.isoformat(),
             'epoch_duration': self.stage.config['prediction_bin_duration']})

        # compose payload
        data = {
            'seismic_catalog': self.forecast.seismiccatalog,
            'well': self.forecast.well,
            'model_parameters': model_parameters,
            'reservoir': self.scenario.reservoirgeom,
            'scenario': {'well': self.scenario.well}, }

        serializer = SFMWorkerIMessageSerializer(
            proj=point_to_proj4(self.project.referencepoint),
            transform_callback=pymap3d_transform_ned2geodetic)
        payload = self._worker_handle.Payload(**data, serializer=serializer)

        try:
            resp = self._worker_handle.compute(
                payload, deserializer=SFMWorkerOMessageDeserializer())
        except RemoteSeismicityWorkerHandle.RemoteWorkerError as err:
            log.error(str(err))
            self.status_changed.emit(
                ExecutionStatus(self, flag=ExecutionStatus.Flag.ERROR))
            return

        status = resp['data']['attributes']['status_code']

        if status != self.TASK_ACCEPTED:
            self.status_changed.emit(self._resp_to_status(resp))
            return

        self.model_run.runid = resp['data']['id']
        self.status_changed.emit(
            ExecutionStatus(self, flag=ExecutionStatus.Flag.STARTED))
        self.timer = QTimer()
        self.timer.timeout.connect(self._poll)
        self.timer.start(self.POLLING_INTERVAL)
        # TODO(damb):
        # The method returns such that the forecast executor notes that both
        # the scenario and the forecast are completed.

    def _poll(self):
        deserializer = SFMWorkerOMessageDeserializer(
            proj=point_to_proj4(self.project.referencepoint),
            transform_callback=pymap3d_transform_geodetic2ned,
            many=True)
        resp = self._worker_handle.query(
            task_ids=self.model_run.runid, deserializer=deserializer).first()

        status = resp['data']['attributes']['status_code']

        if status not in (self.TASK_ACCEPTED, 423):
            self.timer.stop()

        if 200 == status:
            # process result
            # TODO(damb): Perform this validation within the corresponding IO
            # facilities.
            try:
                result = resp['data']['attributes']['forecast']
            except KeyError:
                self.status_changed.emit(ExecutionStatus(
                    self, flag=ExecutionStatus.Flag.ERROR))
            else:
                self.model_run.result = result

        log.info(f'Received response (run={self.model_run!r}, '
                 f'id={self.model_run.runid}): {resp}')
        self.status_changed.emit(self._resp_to_status(resp))

    def _resp_to_status(self, resp):
        """
        Convert a SFM worker response into an :code:`ExecutionStatus`.

        :param dict resp: Response to convert
        """
        return ExecutionStatus(
            self, info=resp,
            flag=self.RESP_MAP[resp['data']['attributes']['status_code']])
