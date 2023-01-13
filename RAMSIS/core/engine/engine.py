# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Forecast executing related engine facilities.
"""
import time
from datetime import datetime
from sqlalchemy.orm import subqueryload
# Still using Qt threading, this will not be used with the transition
# to managing tasks with prefect.

import prefect
from prefect import config
from prefect.engine.flow_runner import FlowRunner as _FlowRunner
from prefect.engine.task_runner import TaskRunner
from prefect.engine.executors import LocalExecutor
from prefect import Flow, Parameter, context
from prefect.executors import LocalDaskExecutor

from ramsis.datamodel import SeismicityModelRun, \
    ReservoirSeismicityPrediction, Forecast, ForecastScenario, \
    EStage, SeismicityForecastStage, HazardStage, Project, EStatus, \
    HazardModelRun, HazardMap, HazardCurve, HazardPointValue

from RAMSIS.db import store, app_settings
from RAMSIS.core.engine import forecast_handler, threadpoolexecutor, \
    synchronous_thread, hazard_preparation_handler, hazard_handler, \
    forecast_context_format


def forecast_for_seismicity(forecast_id, session):
    """
    Returns the forecast for seismicity forcast flow.
    The forecast table is joined to all the tables required.
    """
    session.remove()
    forecast_query = session.query(Forecast).\
        options(
            subqueryload(Forecast.project).
            subqueryload(Project.settings)).\
        options(
            # Load catalogs linked to forecast and project
            subqueryload(Forecast.status)).\
        options(
            # Load catalogs linked to forecast and project
            subqueryload(Forecast.seismiccatalog)).\
        options(
            # Load catalogs linked to forecast and project
            subqueryload(Forecast.well)).\
        options(
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.well)).\
        options(
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage))).\
        options(
            # Load result attributes for model runs (these will be written to)
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage)).\
            subqueryload(SeismicityForecastStage.runs).\
            subqueryload(SeismicityModelRun.forecaststage)).\
        options(
            # Load result attributes for model runs (these will be written to)
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage)).\
            subqueryload(SeismicityForecastStage.runs).\
            subqueryload(SeismicityModelRun.result)).\
        options(
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                HazardStage)).\
            subqueryload(HazardStage.runs).\
            subqueryload(HazardModelRun.hazardmaps).\
            subqueryload(HazardMap.samples).\
            subqueryload(HazardPointValue.geopoint)).\
        options(
            subqueryload(Forecast.scenarios).\
            subqueryload(ForecastScenario.stages.of_type(
                HazardStage)).\
            subqueryload(HazardStage.runs).\
            subqueryload(HazardModelRun.hazardcurves).\
            subqueryload(HazardCurve.samples).\
            subqueryload(HazardPointValue.geopoint)).\
        filter(Forecast.id == forecast_id)
    forecast = forecast_query.one()
    session.remove()
    return forecast


def scenario_for_hazard(scenario_id, session):
    session.remove()
    scenario_query = session.query(ForecastScenario).\
        options(subqueryload(ForecastScenario.forecast)).\
        options(
            subqueryload(ForecastScenario.forecast).
            subqueryload(Forecast.project)).\
        options(
            # Load catalogs linked to forecast and project
            subqueryload(ForecastScenario.forecast).\
            subqueryload(Forecast.status)).\
        options(
            # Load status of seismicity stage
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage))).\
        options(
            # Load result attributes for model runs (these will be written to)
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage)).\
            subqueryload(SeismicityForecastStage.runs).\
            subqueryload(SeismicityModelRun.result).\
            subqueryload(ReservoirSeismicityPrediction.catalogs).\
            subqueryload(ReservoirSeismicityPrediction.samples)).\
        options(
            # Load models from seismicity stage
            subqueryload(ForecastScenario.stages.of_type(
                HazardStage)).\
            subqueryload(HazardStage.runs).\
            subqueryload(HazardModelRun.hazardmaps).\
            subqueryload(HazardMap.samples).\
            subqueryload(HazardPointValue.geopoint)).\
        options(
            subqueryload(ForecastScenario.stages.of_type(
                HazardStage)).\
            subqueryload(HazardStage.runs).\
            subqueryload(HazardModelRun.hazardcurves).\
            subqueryload(HazardCurve.samples).\
            subqueryload(HazardPointValue.geopoint)).\
        options(
            # Load models from seismicity stage
            subqueryload(ForecastScenario.stages.of_type(
                HazardStage)).\
            subqueryload(HazardStage.model)).\
        options(
            # Remove this section, not needed as have new table.
            subqueryload(ForecastScenario.stages.of_type(
                SeismicityForecastStage)).\
            subqueryload(SeismicityForecastStage.runs).\
            subqueryload(SeismicityModelRun.hazardruns)).\
        filter(ForecastScenario.id == scenario_id)
    scenario = scenario_query.one()
    session.remove()
    return scenario


class ForecastFlow:
    """
    Contains prefect flow logic for creating DAG.
    A flow is created for every forecast that is run by the
    engine.
    """

    def __init__(self, forecast, system_time, forecast_handler, session):
        super().__init__()
        self.forecast_handler = forecast_handler
        self.forecast = forecast
        self.system_time = system_time
        self.session = session
        self.state = None

    def run(self):
        from RAMSIS.flows import seismicity_flow
        # (sarsonl) To view DAG: seismicity_flow.visualize()
        executor = LocalDaskExecutor(scheduler='threads')
        seismicity_flow.state_handlers = [
            self.forecast_handler.flow_state_handler]
        context_str = forecast_context_format.format(
            forecast_id=self.forecast.id)
        with context(
                forecast_id=self.forecast.id,
                forecast_context=context_str,
                session=self.session):
            config.engine.executor.default_class = LocalExecutor
            config.engine.flow_runner.default_class = _FlowRunner
            config.engine.task_runner.default_class = TaskRunner
            self.state = seismicity_flow.run(
                forecast=self.forecast,
                system_time=self.system_time,
                executor=executor,
                runner_cls=_FlowRunner)


class HazardFlow:

    def __init__(self, forecast_id, data_dir, system_time):
        self.forecast_id = forecast_id
        self.system_time = system_time
        self.data_dir = data_dir
        self.state = None

    def run(self):
        from RAMSIS.flows import hazard_flow
        #with Flow("Hazard_Preparation_Execution",
        #          state_handlers=[self.hazard_handler.flow_state_handler]
        #          ) as hazard_flow:
        #    forecast_id = Parameter('forecast_id')
        #    data_dir = Parameter('data_dir')
            # Start Hazard stage
            #hazard_runs = CreateHazardModelRuns(
            #    state_handlers=[self.hazard_handler.
            #                    create_hazard_models_state_handler])
            #hazard_model_runs = hazard_runs(scenario)

            #update_hazard_runs = UpdateHazardRuns(
            #    state_handlers=[
            #        self.hazard_handler.update_hazard_models_state_handler])
            #haz_model_runs_updated = update_hazard_runs(hazard_model_runs)

            #create_oq_directories = CreateHazardModelRunDir()
            #oq_input_dir = create_oq_directories.map(unmapped(data_dir),
            #                                         haz_model_runs_updated)
            #oq_static_files = OQFiles()
            #oq_static_files.map(haz_model_runs_updated, oq_input_dir)

            #oq_source_models = OQSourceModelFiles()
            #source_model_xml_basenames = oq_source_models.map(
            #    haz_model_runs_updated, oq_input_dir)

            #oq_logic_tree = OQLogicTree()
            #oq_logic_tree.map(haz_model_runs_updated, oq_input_dir,
            #                  source_model_xml_basenames)
            #prepared_hazard_flow.add_edge(
            #    prepared_hazard_flow.get_tasks('OQFiles')[0],
            #    prepared_hazard_flow.get_tasks('OQLogicTree')[0])


        executor = LocalDaskExecutor(scheduler='threads')
        context_str = forecast_context_format.format(
            forecast_id=self.forecast_id)
        with context(
                forecast_id=self.forecast_id,
                forecast_context=context_str):
            config.engine.executor.default_class = LocalExecutor
            config.engine.flow_runner.default_class = _FlowRunner
            config.engine.task_runner.default_class = TaskRunner
            self.state = hazard_flow.run(
                forecast_id=self.forecast_id,
                data_dir=self.data_dir,
                executor=executor,
                runner_cls=_FlowRunner)



class Engine:
    """
    The engine is responsible for running forecasts
    """

    def __init__(self):
        """
        :param RAMSIS.core.controller.Controller core: Reference to the core
        """
        super().__init__()
        self.session = None

    def run(self, forecast_id):
        """
        Runs the forecast with a prefect flow.

        The :class:`~RAMSIS.core.taskmanager.ForecastTask` invokes this
        whenever a new forecast is due.

        :param forecast: Forecast to execute
        :type forecast: ramsis.datamodel.forecast.Forecast
        """
        if not self.session:
            self.session = store.session
        if app_settings:
            data_dir = app_settings['data_dir']

        self.flow_runner = FlowRunner(
            forecast_id, self.session, data_dir)

        self.flow_runner.run()


class FlowRunner:
    def __init__(self, forecast_id, session, data_dir):
        self.threadpoolexecutor = threadpoolexecutor
        self.synchronous_thread = synchronous_thread
        self.forecast_id = forecast_id
        self.session = session
        self.data_dir = data_dir
        self.system_time = datetime.utcnow()
        self.logger = prefect.utilities.logging.get_logger()
        self.logger.propagate = True
        self.forecast_handler = forecast_handler
        self.hazard_preparation_handler = hazard_preparation_handler
        self.hazard_handler = hazard_handler
        self.stage_results = []

    def update_forecast_status(self, estatus):
        forecast = self.session.query(Forecast).filter(
            Forecast.id == self.forecast_id).first()
        forecast.status.state = estatus
        self.session.commit()
        self.session.remove()

    def get_forecast_starttime(self, forecast_id):
        forecast = self.session.query(Forecast).filter(
            Forecast.id == self.forecast_id).first()
        self.session.remove()
        return forecast.starttime

    def stage_statuses(self, estage):
        self.session.expire_all()
        forecast = self.session.query(Forecast).filter(
            Forecast.id == self.forecast_id).first()
        stage_states_list = []
        for scenario in forecast.scenarios:
            try:
                stage = scenario[estage].status
                stage_states_list.append(stage)
            except KeyError:
                pass
        return stage_states_list

    def seismicity_flow(self, forecast_input):
        seismicity_stage_statuses = self.stage_statuses(EStage.SEISMICITY)
        if any(status.state != EStatus.COMPLETE for status in
                seismicity_stage_statuses):

            forecast_flow = ForecastFlow(forecast_input,
                                         self.system_time,
                                         self.forecast_handler,
                                         self.session)
            forecast_flow.run()

            self.threadpoolexecutor.shutdown(wait=True)
            seismicity_stage_statuses = self.stage_statuses(EStage.SEISMICITY)
        return seismicity_stage_statuses

    def hazard_flow(self, forecast_id):
        hazard_stage_statuses = self.stage_statuses(EStage.HAZARD)
        if any(status.state != EStatus.COMPLETE for status in
                hazard_stage_statuses):

            prefect_hazard_flow = HazardFlow(forecast_id,
                                             self.data_dir,
                                             self.system_time)
            prefect_hazard_flow.run()
            #self.threadpoolexecutor.shutdown(wait=True)
            #while (self.synchronous_thread.model_runs <
            #       self.synchronous_thread.model_runs_count):
            #    time.sleep(5)
            hazard_stage_statuses = self.stage_statuses(EStage.HAZARD)
        return hazard_stage_statuses

    def run_stage(self, forecast_input, estage):
        stage_enabled = False
        try:
            scenarios = forecast_input.scenarios
            for scenario in scenarios:
                if scenario[estage].enabled:
                    stage_enabled = True
        except AttributeError:
            pass
        return stage_enabled

    def run(self):
        self.update_forecast_status(EStatus.RUNNING)
        forecast_input = forecast_for_seismicity(self.forecast_id,
                                                 self.session)
        assert forecast_input.status.state != EStatus.COMPLETE

        if self.run_stage(forecast_input, EStage.SEISMICITY):
            seismicity_stage_states = self.seismicity_flow(forecast_input)
            # Added this to make sure that the state handler has written
            # everything to db before terminating (BUG where prefect
            # killed the process before this was complete, leading to
            # results not being stored)
            self.stage_results.extend(seismicity_stage_states)
            time.sleep(10)
            forecast = self.session.query(Forecast).filter(
                Forecast.id == self.forecast_id).first()
        self.logger.info(f"The stage states are: {self.stage_results}")

        #if self.run_stage(forecast_input, EStage.SEISMICITY):
        #    hazard_stage_states = self.hazard_flow(self.forecast_id)
        #    self.stage_results.extend(hazard_stage_states)

        #print(self.stage_results)

        #forecast = self.session.query(Forecast).filter(
        #    Forecast.id == self.forecast_id).first()
        #statuses = [status.state for status in self.stage_results]
        #if all(state == EStatus.COMPLETE for state in statuses):
        #    self.update_forecast_status(EStatus.COMPLETE)
        #    self.session.commit()
        #    self.session.close()
        #else:
        #    self.logger.error(
        #            f"Not all stages are complete, stage states: {statuses}")
        #    self.update_forecast_status(EStatus.ERROR)
        #    self.session.commit()
        #    self.session.close()
        #    raise Exception("One or more stages have failed.")
