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

import logging
from RAMSIS.core.tools.executor import (Executor, ParallelExecutor,
                                        SerialExecutor, ExecutionStatus)
from RAMSIS.core.tools.notifications import (RunningNotification,
                                             CompleteNotification,
                                             ErrorNotification,
                                             OtherNotification)
from RAMSIS.utils import call_later
from ramsis.datamodel.forecast import SeismicityForecastStage


log = logging.getLogger(__name__)


def _create_execution_status(origin, notification):
    """
    Translates a client/worker notification into an execution status

    :param notification: client/worker notification
    :return: :class:`ExecutionStatus` resulting from notification
    :rtype: :class:`ExecutionStatus`
    """
    # TODO LH: Implement. This is still based on the notifications from the
    #  previous model client implementation
    FLAG_MAP = {
        RunningNotification: ExecutionStatus.Flag.STARTED,
        CompleteNotification: ExecutionStatus.Flag.SUCCESS,
        ErrorNotification: ExecutionStatus.Flag.ERROR,
        OtherNotification: ExecutionStatus.Flag.UPDATE
    }
    return ExecutionStatus(origin, FLAG_MAP[type(notification)],
                           info=notification)


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
        self.setObjectName(f'Forecast at {forecast.starttime}')
        self.core = core
        self.forecast = forecast
        for scenario in forecast.scenarios:
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

        # We may have future events in the live catalog if simulating
        def filter_future(event):
            return event.datetime_value < self.forecast.starttime

        self.forecast.seismiccatalog = self.core.project.seismiccatalog.\
            snapshot(filter_cond=filter_future)

        # We only support one well at the moment
        # TODO LH: assign active well at forecast time (once we have those) or
        #   let the user specify the well at scenario config time.
        #self.forecast.well = self.core.project.wells[0]

    def post_process(self):
        self.core.store.save()
        log.info('Forecast {} completed'.format(self.forecast.starttime))

    def on_child_status_changed(self, status):
        # Do a save whenever intermediate results become available. It's the
        # childrens responsibility to add their respective results to the
        # scenario before the save takes place.
        self.core.store.save()
        super().on_child_status_changed(status)


class ScenarioExecutor(SerialExecutor):
    """
    Runs seismicity forecast, hazard and risk calculation for a scenario

    :param scenario: Scenario for this job
    :type scenario: ramsis.datamodel.forecast.ForecastScenario
    """

    def __init__(self, scenario, **kwargs):
        super().__init__(**kwargs)
        self.setObjectName(scenario.name)
        self.scenario = scenario
        self.forecast = scenario.forecast
        cfg = self.scenario.config
        if cfg['run_is_forecast']:
            SeismicityForecastStageExecutor(self.scenario, parent=self)
        if cfg['run_hazard']:
            HazardStageExecutor(self.scenario, parent=self)
        if cfg['run_risk']:
            RiskStageExecutor(self.scenario, parent=self)

    def pre_process(self):
        log.info(f'Computing scenario: {self.scenario.name}')

    def post_process(self):
        log.info(f'Scenario "{self.scenario.name}" complete')


class SeismicityForecastStageExecutor(ParallelExecutor):
    """
    Implements the seismicity forecast stage.

    Executes all seismicity forecast models for a specific scenario

    :param scenario: Scenario for which to execute model forecasts
    :type scenario: ramsis.datamodel.forecast.ForecastScenario
    """

    def __init__(self, scenario, **kwargs):
        super().__init__(**kwargs)
        self.setObjectName(scenario.name)
        self.scenario = scenario

        # TODO LH: What if there is no forecast stage (if it's disabled - is
        #   that even allowed)?
        stage = next((s for s in scenario.stages
                      if isinstance(s, SeismicityForecastStage)), None)
        for run in stage.runs:
            SeismicityModelRunExecutor(run, parent=self)

    def pre_process(self):
        log.info(f'Starting seismicity forecast stage for scenario '
                 f'"{self.objectName()}"')

    def post_process(self):
        log.info(f'All seismicity forecast models complete for scenario '
                 f'"{self.objectName()}"')


class SeismicityModelRunExecutor(Executor):
    """
    Executes a single seimicity model run

    The executor instantiates the actual model that is associated with the run,
    connects to its status update signal and then calls its run method.

    :param seismicity_model_run: Model run to execute
    :type seismicity_model_run: ramsis.datamodel.seismicity.SeismicityModelRun
    """

    def __init__(self, seismicity_model_run, **kwargs):
        super().__init__(**kwargs)
        self.setObjectName(f'Seismicity Model '
                           f'{seismicity_model_run.model.name}')
        self.model_run = seismicity_model_run
        # TODO: link to (executable) model.
        #   The previous implementation of ModelClient started a polling timer
        #   if the request got accepted by the remote worker). Note: someone
        #   (either this class or the client) has to make sure that we update
        #   the status even if there's a network issue or the worker hangs.
        #   I.e. a timeout must be implemented.

        # TODO: this is just pseudocode
        # model = seismicity_model_run.model
        # model.status_changed.connect(self.on_model_status_changed)

    def run(self):
        log.info(f'Running seismicity forecast model {self.objectName()}')

        # TODO: implement. this is just pseudocode (assuming the .model will
        #   take care of compiling all the relevant input data for the worker)
        # self.model_run.model.run()
        # TODO LH: remove, fake instant success for testing :)
        self.status_changed.emit(ExecutionStatus(self))

    def on_model_status_changed(self, notification):
        pass
        # TODO: if the model we're executing is based of
        #   datamodel.seismicity.SeismicityModel as assumed above, it can
        #   persist its status itself. We just need to translate it into an
        #   executor status here and pass it on.

        # TODO: implement. this is just pseudocode
        # model = self.sender()
        # execution_status = _create_execution_status(self, notification)
        # if notification.success:
        #     self.model_run.result = notification.result
        #
        # self.status_changed.emit(execution_status)


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

    def __init__(self, scenario, **kwargs):
        super().__init__(**kwargs)
        self.setObjectName('Hazard Stage')
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

    def __init__(self, scenario, **kwargs):
        super().__init__(**kwargs)
        self.setObjectName('Risk Stage')
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
