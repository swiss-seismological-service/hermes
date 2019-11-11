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

from PyQt5.QtCore import pyqtSignal, QObject
from ramsis.datamodel.seismicity import SeismicityModelRun
from ramsis.datamodel.forecast import (Forecast, EStage,
                                       ForecastScenario,
                                       ForecastStage)
from ramsis.datamodel.status import EStatus
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
    forecast_submitted = pyqtSignal(object)

    def __init__(self, core, forecast_id, **kwargs):
        super().__init__(**kwargs)
        self.setObjectName(f'{forecast_id!r}')
        self.core = core
        self.forecast = self.core.store.session.query(Forecast).\
            filter(Forecast.id == forecast_id).one_or_none()
        self.forecast_id = forecast_id
        self.session = self.core.store.session
        scenario_ids = [s.id for s in self.forecast.scenarios if s.enabled]
        self.core.store.session.expunge(self.forecast)
        for scenario_id in scenario_ids:
            ScenarioExecutor(scenario_id, self.session, parent=self)

    def run(self, progress_callback):
        super().run()
    #    progress_callback.emit(ExecutionStatus(self,
    #                           ExecutionStatus.Flag.STARTED))
    #    self._iter = iter(self.children())
    #    self.pre_process()
    #    log.info("before run_next {}".format(self.children))
    #    self._run_next()

    def pre_process(self):
        """
        Prepares a forecast for running

        This includes associating the currently active welland taking a
        snapshot of the seismic catalog.

        :param Forecast forecast: Forecast to prepare
        :param datetime run_time: Time at which forecast is run

        """
        log.info(f'Executing {self.objectName()}')
        forecast = self.core.store.session.query(Forecast).\
            filter(Forecast.id == self.forecast_id).one_or_none()
        self.core.store.session.add(forecast)

        # We may have future events in the live data if simulating
        def filter_future(event):
            return event.datetime_value < forecast.starttime

        seismiccatalog = self.core.project.seismiccatalog.\
            snapshot(filter_cond=filter_future)
        seismiccatalog.forecast_id = self.forecast_id
        forecast.seismiccatalog_history.append(seismiccatalog)
        # XXX(damb): We only support one well with a single section at the
        # moment
        well = self.core.project.well.\
            snapshot(sample_filter_cond=filter_future)
        well.forecast_id = self.forecast_id
        forecast.well_history.append(well)
        self.session.commit()
        self.session.expunge(forecast)


class SeismicityForecastStageExecutor(ParallelExecutor):
    """
    Implements the seismicity forecast stage.

    Executes all seismicity forecast models for a specific scenario

    :param scenario: Scenario for which to execute model forecasts
    :type scenario: ramsis.datamodel.forecast.ForecastScenario
    """

    def __init__(self, stage_id, session, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.setObjectName(f'{stage_id!r}')
        self.stage = session.query(ForecastStage).filter(
            ForecastStage.id == stage_id).one_or_none()
        model_run_ids = [r.id for r in self.stage.runs if r.enabled]
        self.session.expunge(self.stage)
        for model_run_id in model_run_ids:
            SeismicityModelRunExecutor(model_run_id, self.session, parent=self)

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

    def __init__(self, session, stage, **kwargs):
        super().__init__(**kwargs)
        self.setObjectName(f'{stage!r}')
        self.session = session
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
        # self.proceed_on[0]execution_status = _create_execution_status(
        #       self, notification)
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

    def __init__(self, stage, session, **kwargs):
        super().__init__(**kwargs)
        self.setObjectName(f'{stage!r}')
        self.session = session
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

    def __init__(self, scenario_id, session, **kwargs):
        super().__init__(**kwargs)
        self.setObjectName(f'{scenario_id!r}')
        self.scenario = session.query(ForecastScenario).\
            filter(ForecastScenario.id == scenario_id).one_or_none()
        self.session = session
        self._setup()

    def _setup(self):

        def execute(stage_type, executor):
            try:
                stage = self.scenario[stage_type]
                stage_id = stage.id
                stage_enabled = stage.enabled
                self.session.expunge(stage)
            except KeyError as err:
                raise ExecutorError(f'Missing stage: {err}')
            else:
                if stage_enabled:
                    executor(stage_id, self.session, parent=self)

        for stage_type, executor in self._EXEC_MAP.items():
            execute(stage_type, executor)
        self.session.expunge(self.scenario)

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
        TASK_ACCEPTED: (ExecutionStatus.Flag.STARTED, EStatus.PENDING),
        200: (ExecutionStatus.Flag.SUCCESS, EStatus.COMPLETE),
        423: (ExecutionStatus.Flag.RUNNING, EStatus.RUNNING),
        418: (ExecutionStatus.Flag.ERROR, EStatus.ERROR),
        204: (ExecutionStatus.Flag.ERROR, EStatus.ERROR),
        405: (ExecutionStatus.Flag.ERROR, EStatus.ERROR),
        422: (ExecutionStatus.Flag.ERROR, EStatus.ERROR),
        500: (ExecutionStatus.Flag.ERROR, EStatus.ERROR), }

    def __init__(self, model_run_id, session, **kwargs):
        """
        :param run: Model run to execute
        :type run: :py:class:`ramsis.datamodel.seismicity.SeismicityModelRun`
        """
        super().__init__(**kwargs)
        self.setObjectName(f'{model_run_id!r}')
        self.session = session
        self.model_run_id = model_run_id

    def run(self):
        self.model_run = self.session.query(SeismicityModelRun).\
            filter(SeismicityModelRun.id == self.model_run_id).one_or_none()
        self.stage = self.model_run.forecaststage
        self.scenario = self.model_run.forecaststage.scenario
        self.forecast = self.model_run.forecaststage.scenario.forecast

        self.project = self.model_run.forecaststage.scenario.forecast.project

        self._worker_handle = RemoteSeismicityWorkerHandle.from_run(
            self.model_run)
        log.info(f'Running seismicity forecast model {self.objectName()}')
        model_parameters = copy.deepcopy(self.model_run.config)
        model_parameters.update(
            {'datetime_start': self.forecast.starttime.isoformat(),
             'datetime_end': self.forecast.endtime.isoformat(),
             'epoch_duration': self.stage.config['prediction_bin_duration']})
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
            self.model_run.status.state = EStatus.ERROR
            self.status_changed.emit(
                ExecutionStatus(self, flag=ExecutionStatus.Flag.ERROR,
                                info=err))
            return

        status = resp['data']['attributes']['status_code']

        if status != self.TASK_ACCEPTED:
            self._update_orm_status(resp)
            self.status_changed.emit(self._resp_to_status(resp))
            return

        self.model_run.runid = resp['data']['id']
        self.model_run.status.state = EStatus.RUNNING
        self.session.commit()
        self.session.expunge(self.model_run)
        self.status_changed.emit(
            ExecutionStatus(self, flag=ExecutionStatus.Flag.RUNNING))

    def _update_orm_status(self, resp):
        self.model_run.status.state = \
            self.RESP_MAP[resp['data']['attributes']['status_code']][1]

    def _resp_to_status(self, resp):
        """
        Convert a SFM worker response into an :code:`ExecutionStatus`.

        :param dict resp: Response to convert
        """
        return ExecutionStatus(
            self, info=resp,
            flag=self.RESP_MAP[resp['data']['attributes']['status_code']][0])


class SeismicityModelRunPoller(QObject):
    """
    Executes a single seimicity model run

    The executor instantiates the actual model that is associated with the run,
    connects to its status update signal and then calls its run method.
    """
    status_changed = pyqtSignal(object)
    POLLING_INTERVAL = 5000
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

    def __init__(self, session, model_run_id, **kwargs):
        """
        :param run: Model run to execute
        :type run: :py:class:`ramsis.datamodel.seismicity.SeismicityModelRun`
        """
        super().__init__(**kwargs)
        log.info("In seismicity model poller")
        self.session = session
        self.model_run = self.session.query(SeismicityModelRun).\
            filter(SeismicityModelRun.runid == model_run_id).one_or_none()
        self.project = self.model_run.forecaststage.scenario.forecast.project

        self._worker_handle = RemoteSeismicityWorkerHandle.from_run(
            self.model_run)

    def poll(self):
        log.info("in poll")
        deserializer = SFMWorkerOMessageDeserializer(
            proj=point_to_proj4(self.project.referencepoint),
            transform_callback=pymap3d_transform_geodetic2ned,
            many=True)
        try:
            resp = self._worker_handle.query(
                task_ids=self.model_run.runid,
                deserializer=deserializer).first()
        except RemoteSeismicityWorkerHandle.RemoteWorkerError as err:
            log.error(str(err))
            self.status_changed.emit(
                ExecutionStatus(self, flag=ExecutionStatus.Flag.ERROR,
                                info=err))
            return

        status = resp['data']['attributes']['status_code']

        if status in (self.TASK_ACCEPTED, 423):
            self.task_status = self.STATUS['ACCEPTED']
            return

        if 200 == status:
            # process result
            # TODO(damb): Perform this validation within the corresponding IO
            # facilities.
            try:
                result = resp['data']['attributes']['forecast']
            except KeyError:
                self.model_run.status.state = EStatus.ERROR
                self.status_changed.emit(ExecutionStatus(
                    self, flag=ExecutionStatus.Flag.ERROR))
            else:
                self.model_run.result = result
                self.task_status = self.STATUS['SUCCESS']

        log.info(f'Received response (run={self.model_run!r}, '
                 f'id={self.model_run.runid}): {resp}')

        self._update_orm_status(resp)
        self.status_changed.emit(self._resp_to_status(resp))
        self.session.commit()

    def _update_orm_status(self, resp):
        self.model_run.status.state = \
            self.RESP_MAP[resp['data']['attributes']['status_code']][1]

    def _resp_to_status(self, resp):
        """
        Convert a SFM worker response into an :code:`ExecutionStatus`.

        :param dict resp: Response to convert
        """
        return ExecutionStatus(
            self, info=resp,
            flag=self.RESP_MAP[resp['data']['attributes']['status_code']][0])
