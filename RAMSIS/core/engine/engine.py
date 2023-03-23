## Copyright 2018, ETH Zurich - Swiss Seismological Service SED
#"""
#Forecast executing related engine facilities.
#"""
#from datetime import datetime
#from sqlalchemy.orm import subqueryload
## Still using Qt threading, this will not be used with the transition
## to managing tasks with prefect.
#
#import prefect
##from prefect import config
#from prefect.engine.flow_runner import FlowRunner as _FlowRunner
#from prefect.engine.task_runner import TaskRunner
#from prefect.engine.executors import LocalExecutor
#from prefect import context
#from prefect.executors import LocalDaskExecutor
#
#from ramsis.datamodel import SeismicityModelRun, \
#    ReservoirSeismicityPrediction, Forecast, ForecastScenario, \
#    EStage, SeismicityForecastStage, HazardStage, Project, EStatus, \
#    HazardModelRun, HazardMap, HazardCurve, HazardPointValue
#
#from RAMSIS.db import store, app_settings
#from RAMSIS.core.engine import forecast_handler, threadpoolexecutor, \
#    synchronous_thread, hazard_preparation_handler, hazard_handler, \
#    forecast_context_format
#
#
#def forecast_for_seismicity(forecast_id, session):
#    """
#    Returns the forecast for seismicity forcast flow.
#    The forecast table is joined to all the tables required.
#    """
#    session.remove()
#    forecast_query = session.query(Forecast).\
#        options(
#            subqueryload(Forecast.project).
#            subqueryload(Project.settings)).\
#        options(
#            # Load catalogs linked to forecast and project
#            subqueryload(Forecast.status)).\
#        options(
#            # Load catalogs linked to forecast and project
#            subqueryload(Forecast.seismiccatalog)).\
#        options(
#            # Load catalogs linked to forecast and project
#            subqueryload(Forecast.well)).\
#        options(
#            subqueryload(Forecast.scenarios).\
#            subqueryload(ForecastScenario.well)).\
#        options(
#            subqueryload(Forecast.scenarios).\
#            subqueryload(ForecastScenario.stages.of_type(
#                SeismicityForecastStage))).\
#        options(
#            # Load result attributes for model runs (these will be written to)
#            subqueryload(Forecast.scenarios).\
#            subqueryload(ForecastScenario.stages.of_type(
#                SeismicityForecastStage)).\
#            subqueryload(SeismicityForecastStage.runs).\
#            subqueryload(SeismicityModelRun.forecaststage)).\
#        options(
#            # Load result attributes for model runs (these will be written to)
#            subqueryload(Forecast.scenarios).\
#            subqueryload(ForecastScenario.stages.of_type(
#                SeismicityForecastStage)).\
#            subqueryload(SeismicityForecastStage.runs).\
#            subqueryload(SeismicityModelRun.result)).\
#        options(
#            subqueryload(Forecast.scenarios).\
#            subqueryload(ForecastScenario.stages.of_type(
#                HazardStage)).\
#            subqueryload(HazardStage.runs).\
#            subqueryload(HazardModelRun.hazardmaps).\
#            subqueryload(HazardMap.samples).\
#            subqueryload(HazardPointValue.geopoint)).\
#        options(
#            subqueryload(Forecast.scenarios).\
#            subqueryload(ForecastScenario.stages.of_type(
#                HazardStage)).\
#            subqueryload(HazardStage.runs).\
#            subqueryload(HazardModelRun.hazardcurves).\
#            subqueryload(HazardCurve.samples).\
#            subqueryload(HazardPointValue.geopoint)).\
#        filter(Forecast.id == forecast_id)
#    forecast = forecast_query.one()
#    session.remove()
#    return forecast
#
#
#def scenario_for_hazard(scenario_id, session):
#    session.remove()
#    scenario_query = session.query(ForecastScenario).\
#        options(subqueryload(ForecastScenario.forecast)).\
#        options(
#            subqueryload(ForecastScenario.forecast).
#            subqueryload(Forecast.project)).\
#        options(
#            # Load catalogs linked to forecast and project
#            subqueryload(ForecastScenario.forecast).\
#            subqueryload(Forecast.status)).\
#        options(
#            # Load status of seismicity stage
#            subqueryload(ForecastScenario.stages.of_type(
#                SeismicityForecastStage))).\
#        options(
#            # Load result attributes for model runs (these will be written to)
#            subqueryload(ForecastScenario.stages.of_type(
#                SeismicityForecastStage)).\
#            subqueryload(SeismicityForecastStage.runs).\
#            subqueryload(SeismicityModelRun.result).\
#            subqueryload(ReservoirSeismicityPrediction.catalogs).\
#            subqueryload(ReservoirSeismicityPrediction.samples)).\
#        options(
#            # Load models from seismicity stage
#            subqueryload(ForecastScenario.stages.of_type(
#                HazardStage)).\
#            subqueryload(HazardStage.runs).\
#            subqueryload(HazardModelRun.hazardmaps).\
#            subqueryload(HazardMap.samples).\
#            subqueryload(HazardPointValue.geopoint)).\
#        options(
#            subqueryload(ForecastScenario.stages.of_type(
#                HazardStage)).\
#            subqueryload(HazardStage.runs).\
#            subqueryload(HazardModelRun.hazardcurves).\
#            subqueryload(HazardCurve.samples).\
#            subqueryload(HazardPointValue.geopoint)).\
#        options(
#            # Load models from seismicity stage
#            subqueryload(ForecastScenario.stages.of_type(
#                HazardStage)).\
#            subqueryload(HazardStage.model)).\
#        options(
#            # Remove this section, not needed as have new table.
#            subqueryload(ForecastScenario.stages.of_type(
#                SeismicityForecastStage)).\
#            subqueryload(SeismicityForecastStage.runs).\
#            subqueryload(SeismicityModelRun.hazardruns)).\
#        filter(ForecastScenario.id == scenario_id)
#    scenario = scenario_query.one()
#    session.remove()
#    return scenario
#
#
#class ForecastFlow:
#    """
#    Contains prefect flow logic for creating DAG.
#    A flow is created for every forecast that is run by the
#    engine.
#    """
#
#    def __init__(self, forecast, system_time, forecast_handler, session):
#        super().__init__()
#        self.forecast_handler = forecast_handler
#        self.forecast = forecast
#        self.system_time = system_time
#        self.session = session
#        self.state = None
#
#    def run(self):
#        from RAMSIS.flows import seismicity_flow
#        # (sarsonl) To view DAG: seismicity_flow.visualize()
#        executor = LocalDaskExecutor(scheduler='threads')
#        seismicity_flow.state_handlers = [
#            self.forecast_handler.flow_state_handler]
#        context_str = forecast_context_format.format(
#            forecast_id=self.forecast.id)
#        with context(
#                forecast_id=self.forecast.id,
#                forecast_context=context_str,
#                session=self.session):
#            #config.engine.executor.default_class = LocalExecutor
#            #config.engine.flow_runner.default_class = _FlowRunner
#            #config.engine.task_runner.default_class = TaskRunner
#            self.state = seismicity_flow.run(
#                forecast=self.forecast,
#                system_time=self.system_time,
#                executor=executor,
#                runner_cls=_FlowRunner)
#
#
#class Engine:
#    """
#    The engine is responsible for running forecasts
#    """
#
#    def __init__(self):
#        """
#        :param RAMSIS.core.controller.Controller core: Reference to the core
#        """
#        super().__init__()
#        self.session = None
#
#    def run(self, forecast_id):
#        """
#        Runs the forecast with a prefect flow.
#
#        The :class:`~RAMSIS.core.taskmanager.ForecastTask` invokes this
#        whenever a new forecast is due.
#
#        :param forecast: Forecast to execute
#        :type forecast: ramsis.datamodel.forecast.Forecast
#        """
#        if not self.session:
#            self.session = store.session
#        if app_settings:
#            data_dir = app_settings['data_dir']
#
#        self.flow_runner = FlowRunner(
#            forecast_id, self.session, data_dir)
#
#        self.flow_runner.run()
#
#
#class FlowRunner:
#    def __init__(self, forecast_id, session, data_dir):
#        self.threadpoolexecutor = threadpoolexecutor
#        self.synchronous_thread = synchronous_thread
#        self.forecast_id = forecast_id
#        self.session = session
#        self.data_dir = data_dir
#        self.system_time = datetime.utcnow()
#        self.logger = prefect.utilities.logging.get_logger()
#        self.logger.propagate = True
#        self.forecast_handler = forecast_handler
#        self.hazard_preparation_handler = hazard_preparation_handler
#        self.hazard_handler = hazard_handler
#        self.stage_results = []
#
#    def update_forecast_status(self, estatus):
#        forecast = self.session.query(Forecast).filter(
#            Forecast.id == self.forecast_id).first()
#        forecast.status.state = estatus
#        self.session.commit()
#        self.session.remove()
#
#    def get_forecast_starttime(self, forecast_id):
#        forecast = self.session.query(Forecast).filter(
#            Forecast.id == self.forecast_id).first()
#        self.session.remove()
#        return forecast.starttime
#
#    def stage_statuses(self, estage):
#        self.session.expire_all()
#        forecast = self.session.query(Forecast).filter(
#            Forecast.id == self.forecast_id).first()
#        stage_states_list = []
#        for scenario in forecast.scenarios:
#            try:
#                state = scenario[estage].status.state
#                stage_states_list.append(state)
#            except KeyError:
#                pass
#        return stage_states_list
#
#    def seismicity_flow(self, forecast_input):
#        seismicity_stage_statuses = self.stage_statuses(EStage.SEISMICITY)
#        if any(state != EStatus.COMPLETE for state in
#                seismicity_stage_statuses):
#            self.logger.info("At least one seismicity stage has not "
#                             "completed for this forecast, running "
#                             "ForecastFlow")
#
#            forecast_flow = ForecastFlow(forecast_input,
#                                         self.system_time,
#                                         self.forecast_handler,
#                                         self.session)
#            forecast_flow.run()
#
#            self.threadpoolexecutor.shutdown(wait=True)
#            seismicity_stage_statuses = self.stage_statuses(EStage.SEISMICITY)
#        else:
#            self.logger.info("Not running ForecastFlow")
#        return seismicity_stage_statuses
#
#    def run_stage(self, forecast_input, estage):
#        stage_enabled = False
#        try:
#            scenarios = forecast_input.scenarios
#            for scenario in scenarios:
#                if scenario[estage].enabled:
#                    stage_enabled = True
#        except AttributeError:
#            pass
#        return stage_enabled
#
#    def run(self):
#        forecast_input = forecast_for_seismicity(self.forecast_id,
#                                                 self.session)
#        if forecast_input.status.state == EStatus.COMPLETE:
#            self.logger.info("Forecast is complete, exiting flow.")
#            raise Exception("Forecast is already complete")
#
#        self.update_forecast_status(EStatus.RUNNING)
#
#        if self.run_stage(forecast_input, EStage.SEISMICITY):
#            seismicity_stage_states = self.seismicity_flow(forecast_input)
#            # Added this to make sure that the state handler has written
#            # everything to db before terminating (BUG where prefect
#            # killed the process before this was complete, leading to
#            # results not being stored)
#            self.stage_results.extend(seismicity_stage_states)
#        self.logger.info(f"The stage states are: {self.stage_results}")
#        if all([s == EStatus.COMPLETE for s in self.stage_results]):
#            self.update_forecast_status(EStatus.COMPLETE)
#            self.logger.info("The forecast is now complete")
#        elif any([s == EStatus.ERROR for s in self.stage_results]):
#            self.update_forecast_status(EStatus.ERROR)
#            self.logger.info("The forecast cannot")
#            raise Exception("Stages did not complete successfully.")
#        else:
#            self.logger.info("There are stages that are not complete.")
