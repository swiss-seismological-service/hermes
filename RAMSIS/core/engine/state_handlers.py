import prefect
from sqlalchemy.orm import lazyload, subqueryload
from time import time, sleep
from prefect.engine.result import NoResultType
from PyQt5.QtCore import pyqtSignal, QObject, QRunnable, pyqtSlot

from ramsis.datamodel.status import EStatus
from ramsis.datamodel.seismicity import SeismicityModelRun
from ramsis.datamodel.hazard import HazardModelRun, GeoPoint,\
    HazardPointValue, HazardCurve, HazardMap
from ramsis.datamodel.forecast import EStage, Forecast, ForecastScenario
import logging

logger = logging.getLogger('status_handler')


class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup,
    signals and wrap-up.

    :param callback: The function callback to run on this
    worker thread. Supplied args and
        kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function
    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        # Timeout for a worker to wait for the synchronous thread
        # to be released
        self.timeout = 1000

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''
        synchronous_thread = self.kwargs.pop('synchronous_thread', None)
        if synchronous_thread is not None:
            timeout = time() + self.timeout
            while synchronous_thread.is_reserved():
                sleep(0.5)
                if time() > timeout:
                    raise TimeoutError(
                        "Synchronous thread task taking too long to complete")
                    break
            synchronous_thread.reserve_thread()
        try:
            self.fn(*self.args, **self.kwargs)
        except Exception as err:
            logger.error(f"Synchronous thread Exception raised: {err}")
            raise err
        if synchronous_thread is not None:
            synchronous_thread.release_thread()


class BaseHandler(QObject):
    """
    Handles status changes and results emitted from prefect
    flows. SQLalchemy model objects that are returned are
    merged back into the database and pyqt signals alert the
    GUI to display changes.

    This class is initialized at the same time as the Engine,
    so the session is attached later.

    Prefect status handlers follow the form:
    :param obj: The task that the status update is from
    :param old_state: prefect.engine.state
    :param new_state: prefect.engine.state
    """
    execution_status_update = pyqtSignal(object)
    forecast_status_update = pyqtSignal(object)

    def __init__(self, threadpool, synchronous_thread):
        super().__init__()
        self.session = None
        self.threadpool = threadpool
        self.synchronous_thread = synchronous_thread

    def update_db(self):
        if self.session.dirty:
            self.session.commit()
        self.session.remove()

    def commit(self):
        if self.session.dirty:
            self.session.commit()

    def session_remove(self):
        self.session.remove()

    def state_evaluator(self, new_state, func_list):
        conditions_met = True
        for func in func_list:
            if not func(new_state):
                conditions_met = False
        return conditions_met

    def task_running(self, new_state):
        conditions_met = False
        if (new_state.is_running() and not
            new_state.is_skipped() and not
            new_state.is_mapped() and not
                new_state.is_looped()):
            conditions_met = True
        return conditions_met

    def task_finished(self, new_state):
        conditions_met = False
        if (new_state.is_finished() and not
            new_state.is_skipped() and not
            new_state.is_mapped() and not
                new_state.is_looped()):
            conditions_met = True
        return conditions_met

    def successful_result(self, new_state):
        conditions_met = False
        if (new_state.is_successful() and not
                isinstance(new_state.result, NoResultType)):
            conditions_met = True
        return conditions_met

    def error_result(self, new_state):
        conditions_met = False
        if (new_state.is_failed() and not
                isinstance(new_state.result, NoResultType)):
            conditions_met = True
        return conditions_met


class ForecastHandler(BaseHandler):
    """
    Handles status changes and results emitted from prefect
    flows. SQLalchemy model objects that are returned are
    merged back into the database and pyqt signals alert the
    GUI to display changes.

    This class is initialized at the same time as the Engine,
    so the session is attached later.

    Prefect status handlers follow the form:
    :param obj: The task that the status update is from
    :param old_state: prefect.engine.state
    :param new_state: prefect.engine.state
    """
    def scenario_stage_status(self, scenario):
        # If all model runs are complete without error, then the
        stage = scenario[EStage.SEISMICITY]
        # stage is a success
        model_success = all([
            True if model.status.state == EStatus.COMPLETE else False
            for model in [r for r in stage.runs if r.enabled]])
        if model_success:
            stage.status.state = EStatus.COMPLETE
        else:
            stage.status.state = EStatus.ERROR

        # If all stages are complete without error, then the
        # scenario is a success
        stage_states = [stage.status.state for stage in
                        [s for s in scenario.stages if s.enabled]]
        if all([state == EStatus.COMPLETE
                for state in stage_states]):
            scenario.status.state = EStatus.COMPLETE
        elif any([state == EStatus.ERROR
                  for state in stage_states]):
            scenario.status.state = EStatus.ERROR
        elif any([state == EStatus.PENDING
                 for state in stage_states]):
            scenario.status.state = EStatus.RUNNING

        self.execution_status_update.emit((
            scenario.status.state, type(scenario),
            scenario.id))
        return scenario

    def flow_state_handler(self, obj, old_state, new_state):
        """
        Set the forecast state according to the end state
        of the flow.
        """
        logger = prefect.context.get("logger")
        forecast_id = prefect.context.forecast_id
        worker = Worker(self.update_seismicity_statuses, new_state, logger,
                        forecast_id,
                        synchronous_thread=self.synchronous_thread)
        self.threadpool.start(worker)

    def update_seismicity_statuses(self, new_state, logger, forecast_id):
        forecast = self.session.query(Forecast).filter(
            Forecast.id == forecast_id).first()

        if new_state.is_running():
            forecast.status.state = EStatus.RUNNING
            for scenario in forecast.scenarios:
                if scenario.enabled:
                    scenario.status.state = EStatus.RUNNING
                try:
                    seismicity_stage = scenario[EStage.SEISMICITY]
                    seismicity_stage.status.state = EStatus.RUNNING
                except KeyError:
                    pass
            self.update_db()

        elif new_state.is_finished():
            for scenario in forecast.scenarios:
                scenario = self.scenario_stage_status(scenario)

            self.update_db()
        return new_state

    def scenario_models_state_handler(self, obj, old_state, new_state):
        """
        Set the model runs status to RUNNING when this task suceeds.
        """
        if self.state_evaluator(new_state, [self.task_finished,
                                            self.successful_result]):
            model_runs = new_state.result
            for run in model_runs:
                run.status.state = EStatus.RUNNING
                self.session.commit()
            self.update_db()
        return new_state

    def model_run_state_handler(self, obj, old_state, new_state):
        """
        The seismicity model run task sends a Sucessful state
        when the remote model worker has accepted a task.
        A Failed state is sent from the task otherwise.

        A pyqt signal will be sent on success or failure of the task.
        """
        logger = prefect.context.get("logger")

        if self.state_evaluator(new_state, [self.task_finished]):
            worker = Worker(self.dispatched_model_run, new_state, logger)
            self.threadpool.start(worker)
        return new_state

    def dispatched_model_run(self, new_state, logger):
        if self.state_evaluator(new_state, [self.successful_result]):
            model_run = new_state.result

            update_model_run = self.session.query(SeismicityModelRun).\
                filter(SeismicityModelRun.id == model_run.id).first()
            update_model_run.runid = model_run.runid
            logger.info(
                f"Seismicity model run with runid={model_run.runid}"
                "has been dispatched to the remote worker.")
            update_model_run.status.state = model_run.status.state
        elif self.state_evaluator(new_state, [self.error_result]):
            # prefect Fail should be raised with model_run as a result
            logger.warning(
                f"Seismicity model run has failed: {new_state.result}. "
                f"Message: {new_state.message}")
            model_run = new_state.result
            update_model_run = self.session.query(SeismicityModelRun).\
                filter(SeismicityModelRun.id == model_run.id).first()
            update_model_run.status.state = EStatus.ERROR

        # The sent status is not used, as the whole scenario must
        # be refreshed from the db in the gui thread.

        self.update_db()
        self.execution_status_update.emit((
            new_state, type(model_run),
            model_run.id))

    def poll_seismicity_state_handler(self, obj, old_state, new_state):
        """
        The polling task sends a Sucessful state when the remote
        model worker has returned a forecast and this has been
        deserialized sucessfully. A Failed state is sent from the
        task otherwise.
        A pyqt signal will be sent on success or failure of the task.
        """
        # sarsonl: pass logger from the context in the main thread
        logger = prefect.context.get("logger")

        if self.state_evaluator(new_state, [self.task_finished]):
            if self.state_evaluator(new_state, [self.successful_result]):
                model_run, model_result = new_state.result
                logger.info(f"Seismicity model with runid={model_run.runid} "
                            "has returned without error from the "
                            "remote worker.")
                update_model_run = self.session.query(SeismicityModelRun).\
                    filter(SeismicityModelRun.id == model_run.id).first()
                update_model_run.status.state = EStatus.COMPLETE
                self.update_db()
                worker = Worker(self.finished_model_run, new_state, logger,
                                synchronous_thread=self.synchronous_thread)
                self.threadpool.start(worker)

            elif self.state_evaluator(new_state, [self.error_result]):
                model_run = new_state.result
                logger.error(f"Seismicity model with runid={model_run.runid}"
                             "has returned an error from the "
                             "remote worker.")
                update_model_run = self.session.query(SeismicityModelRun).\
                    filter(SeismicityModelRun.id == model_run.id).first()
                update_model_run.status.state = EStatus.ERROR
                self.update_db()
            self.execution_status_update.emit((
                new_state, type(model_run),
                model_run.id))
        return new_state

    def finished_model_run(self, new_state, logger):
        """
        Adding the result to the database may take time and as this task
        being completed in a timely fashion does not impact the flow, this
        can be moved to another thread.
        """
        model_run, model_result = new_state.result
        update_model_run = self.session.query(SeismicityModelRun).\
            filter(SeismicityModelRun.id == model_run.id).first()
        update_model_run.result = model_result
        self.session.add(model_result)
        self.update_db()

    def add_catalog(self, new_state, logger):
        forecast = new_state.result
        # A forecast may only have one seismiccatalog associated
        # This is enforced in code rather than at db level.
        assert(len(forecast.seismiccatalog) == 1)
        if forecast.seismiccatalog[0] not in self.session():
            self.session.add(forecast.seismiccatalog[0])
            self.session.commit()
            self.session.merge(forecast)
            self.update_db()
            logger.info(f"Forecast id={forecast.id} has made a snapshot"
                        " of the seismic catalog")
        else:
            logger.info(f"Forecast id={forecast.id} already has a snapshot"
                        " of the seismic catalog. "
                        "No new snapshot is being made.")

    def catalog_snapshot_state_handler(self, obj, old_state, new_state):
        """
        When the catalog snapshot task has been skipped, then the forecast
        already has a catalog snapshot and this is not overwritten.
        If this task has completed successfully, the new snapshot is added
        to the session and forecast merged as an attribute was modified.
        """
        logger = prefect.context.get("logger")
        if self.state_evaluator(new_state, [self.task_finished,
                                            self.successful_result]):

            worker = Worker(self.add_catalog, new_state, logger,
                            synchronous_thread=self.synchronous_thread)
            self.threadpool.start(worker)
        return new_state

    def add_well(self, new_state, logger, **kwargs):
        forecast = new_state.result
        # A forecast may only have one well associated
        # This is enforced in code rather than at db level.
        assert(len(forecast.well) == 1)
        if forecast.seismiccatalog[0] not in self.session():
            self.session.add(forecast.well[0])
            self.session.commit()
            self.session.merge(forecast)
            self.update_db()
            logger.info(f"Forecast id={forecast.id} has made a snapshot"
                        " of the hydraulic well")
        else:
            logger.info(f"Forecast id={forecast.id} already has a snapshot"
                        " of the hydraulic well. "
                        "No new snapshot is being made.")

    def well_snapshot_state_handler(self, obj, old_state, new_state):
        """
        When the well snapshot task has been skipped, then the forecast
        already has a well snapshot and this is not overwritten.
        If this task has completed successfully, the new snapshot is added
        to the session and forecast merged as an attribute was modified.
        """
        logger = prefect.context.get("logger")
        if self.state_evaluator(new_state, [self.task_finished,
                                            self.successful_result]):
            worker = Worker(self.add_well, new_state, logger,
                            synchronous_thread=self.synchronous_thread)
            self.threadpool.start(worker)
        return new_state


class HazardPreparationHandler(BaseHandler):
    """
    Handles status changes and results emitted from prefect
    flows. SQLalchemy model objects that are returned are
    merged back into the database and pyqt signals alert the
    GUI to display changes.

    This class is initialized at the same time as the Engine,
    so the session is attached later.

    Prefect status handlers follow the form:
    :param obj: The task that the status update is from
    :param old_state: prefect.engine.state
    :param new_state: prefect.engine.state
    """
    def update_hazard_statuses(self, new_state, logger, scenario_id):
        scenario = self.session.query(ForecastScenario).filter(
            ForecastScenario.id == scenario_id).first()

        if new_state.is_running():
            scenario.forecast.status.state = EStatus.RUNNING
            if scenario.enabled:
                scenario.status.state = EStatus.RUNNING
        try:
            hstage = scenario[EStage.HAZARD]
            if not hstage.enabled:
                self.update_db()
                return new_state
        except KeyError:
            pass
        else:
            if new_state.is_failed():
                self.stages_status_update(hstage, EStatus.ERROR, new_state)

            elif new_state.is_finished() and new_state.is_successful():
                self.stages_status_update(hstage, EStatus.PREPARED, new_state)
                for hrun in hstage.runs:
                    hrun.status.state = EStatus.PREPARED
            self.update_db()
        return new_state

    def stages_status_update(self, stage, status, new_state):
        stage.status.state = status
        for hazard_run in stage.runs:
            if hazard_run.enabled and status == EStatus.PREPARED:
                hazard_run.status.state = status
        self.update_db()
        self.execution_status_update.emit((
            new_state, type(stage),
            None))

    def flow_state_handler(self, obj, old_state, new_state):
        """
        Set the forecast state according to the end state
        of the flow.
        """
        logger = prefect.context.get("logger")
        scenario_id = prefect.context.scenario_id
        worker = Worker(self.update_hazard_statuses, new_state, logger,
                        scenario_id,
                        synchronous_thread=self.synchronous_thread)
        self.threadpool.start(worker)

    def create_hazard_models_state_handler(self, obj, old_state, new_state):
        """
        Adds the new hazard model run to the database.
        """
        if self.state_evaluator(new_state, [self.task_finished,
                                            self.successful_result]):
            runs = new_state.result
            for run in runs:
                run.status.state = EStatus.RUNNING
                self.session.add(run)
                self.update_db()
            if runs:
                run = runs[0]
                stage = run.forecaststage
                stage.status.state = EStatus.RUNNING
                self.execution_status_update.emit((
                    new_state, type(run),
                    None))
        return new_state

    def update_hazard_models_state_handler(self, obj, old_state, new_state):
        """
        Updates the hazard model run with linked seismicity
        runs that are used in making the hazard model.
        """
        if self.state_evaluator(new_state, [self.task_finished,
                                            self.successful_result]):
            runs = new_state.result
            for run in runs:
                hazard_run = self.session.query(HazardModelRun).\
                    filter(HazardModelRun.id == run.id).first()

                for seis_run in run.seismicitymodelruns:
                    update_seis_run = self.session.query(SeismicityModelRun).\
                        filter(SeismicityModelRun.id == seis_run.id).first()
                    update_seis_run.hazardruns.append(hazard_run)
                self.update_db()
        return new_state


class HazardHandler(BaseHandler):
    """
    Handles status changes and results emitted from prefect
    flows. SQLalchemy model objects that are returned are
    merged back into the database and pyqt signals alert the
    GUI to display changes.

    This class is initialized at the same time as the Engine,
    so the session is attached later.

    Prefect status handlers follow the form:
    :param obj: The task that the status update is from
    :param old_state: prefect.engine.state
    :param new_state: prefect.engine.state
    """
    def update_hazard_statuses(self, new_state, logger, scenario_id):
        scenario = self.session.query(ForecastScenario).filter(
            ForecastScenario.id == scenario_id).first()

        if new_state.is_finished():
            scenario = self.scenario_stage_status(scenario, new_state)

            self.update_db()
        return new_state

    def flow_state_handler(self, obj, old_state, new_state):
        """
        Set the scenario state according to the end state
        of the flow.
        """
        print("start flow state handler")
        logger = prefect.context.get("logger")
        scenario_id = prefect.context.scenario_id
        worker = Worker(self.update_hazard_statuses, new_state, logger,
                        scenario_id,
                        synchronous_thread=self.synchronous_thread)
        self.threadpool.start(worker)

    def scenario_stage_status(self, scenario, new_state):
        # If all model runs are complete without error, then the
        stage = scenario[EStage.HAZARD]
        # stage is a success
        model_success = all([
            True if model.status.state == EStatus.COMPLETE else False
            for model in [r for r in stage.runs if r.enabled]])
        if model_success:
            stage.status.state = EStatus.COMPLETE
        else:
            stage.status.state = EStatus.ERROR

        # If all stages are complete without error, then the
        # scenario is a success
        # TODO sarsonl: need to check that not only is the stage enabled,
        # but also that there are models/model runs associated
        stage_success = all([
            True if stage.status.state == EStatus.COMPLETE else False
            for stage in [s for s in scenario.stages if s.enabled]])
        if stage_success:
            scenario.status.state = EStatus.COMPLETE
        else:
            scenario.status.state = EStatus.ERROR

        self.execution_status_update.emit((
            new_state, type(stage),
            stage.id))
        return scenario

    def model_run_state_handler(self, obj, old_state, new_state):
        """
        After the hazard model run has beeen submitted to
        OpenQuake, the model run is updated with a runid
        equivalent to the oq 'job_id'.
        """
        logger = prefect.context.get("logger")

        if self.state_evaluator(new_state, [self.task_finished]):
            model_run = new_state.result
            self.synchronous_thread.model_runs += 1
            if self.state_evaluator(new_state, [self.successful_result]):
                update_model_run = self.session.query(HazardModelRun).\
                    filter(HazardModelRun.id == model_run.id).first()
                update_model_run.runid = model_run.runid
                logger.info(
                    f"Hazard model run with runid={model_run.runid}"
                    "has been dispatched to the remote worker.")
                update_model_run.status.state = model_run.status.state
                self.execution_status_update.emit((
                    new_state, type(model_run),
                    model_run.id))
            elif self.state_evaluator(new_state, [self.error_result]):
                logger.warning(
                    f"Hazard model run has failed: {new_state.result}. "
                    f"Message: {new_state.message}")
                update_model_run = self.session.query(HazardModelRun).\
                    filter(HazardModelRun.id == model_run.id).first()
                update_model_run.status.state = EStatus.ERROR
                self.execution_status_update.emit((
                    new_state, type(model_run),
                    model_run.id))

                # The sent status is not used, as the whole scenario must
                # be refreshed from the db in the gui thread.
            self.update_db()
        return new_state

    def poll_hazard_state_handler(self, obj, old_state, new_state):
        """
        Handles result from hazard model run poller.
        """
        logger = prefect.context.get("logger")
        if self.state_evaluator(new_state, [self.task_finished]):
            worker = Worker(self.oq_hazard_results, new_state, logger,
                            synchronous_thread=self.synchronous_thread)
            self.threadpool.start(worker)
        self.session.remove()
        return new_state

    def add_hc_geopoints(self, result, model_run, result_type='curve'):
        """
        Check if the geopoint location exists in the database
        and use this one if so. Add the new objects to the
        database.

        :param curve: New hazard curve object where child
            attributes must be added or updated in database
        """
        new_samples = []
        for sample in result['samples']:
            hazardpoint = sample['hazardpointvalue']
            geopoint_dict = sample['geopoint_dict']
            geopoint_existing = self.session.query(
                GeoPoint).filter(
                    GeoPoint.lat == geopoint_dict['lat'],
                    GeoPoint.lon == geopoint_dict['lon']).\
                one_or_none()
            if geopoint_existing:
                hazardpoint.geopoint = geopoint_existing
            else:
                hazardpoint.geopoint = GeoPoint(
                    lat=geopoint_dict['lat'],
                    lon=geopoint_dict['lon'],
                    hazardpointvalues=[hazardpoint])
                self.session.add(hazardpoint.geopoint)
            self.session.commit()
            new_samples.append(hazardpoint)
        return new_samples

    def oq_hazard_results(self, new_state, logger):
        """
        The polling task sends a Sucessful state when the remote
        model worker has returned a scenario and this has been
        deserialized sucessfully. A Failed state is sent from the
        task otherwise.
        A pyqt signal will be sent on success or failure of the task.
        """

        if self.state_evaluator(new_state, [self.successful_result]):
            model_run, model_results = new_state.result
            logger.info(f"Hazard model with runid={model_run.runid} "
                        "has returned without error from the "
                        "remote worker.")
            model_run_db = self.session.query(HazardModelRun).\
                options(lazyload(HazardModelRun.forecaststage)).\
                options(lazyload(HazardModelRun.seismicitymodelruns)).\
                filter(HazardModelRun.id == model_run.id).first()

            for result in model_results:
                for results_dict in result:
                    hazard_maps_list = results_dict['hazard_maps']
                    for map_list in hazard_maps_list:
                        hazard_maps = map_list['hazardmap']
                        hazard_maps_new = []

                        for hmap in hazard_maps:
                            hmap = self.add_hc_geopoints(
                                hmap, model_run, result_type='map')
                            hazard_map = HazardMap(
                                samples=hmap, modelrun=model_run_db)
                            hazard_maps_new.append(hazard_map)
                            self.session.commit()

                    hazard_curves_list = results_dict['hazard_curves']
                    for curve_list in hazard_curves_list:
                        hazard_curves = curve_list['hazardcurve']
                        hazard_curves_new = []

                        for curve in hazard_curves:
                            curve = self.add_hc_geopoints(
                                curve, model_run, result_type='curve')
                            hazard_curve = HazardCurve(
                                samples=curve, modelrun=model_run_db)
                            hazard_curves_new.append(hazard_curve)
                            self.session.commit()

            logger.info(f"Hazard model with runid={model_run.runid} "
                        "has returned without error from the "
                        "remote worker.")
            model_run_db.status.state = EStatus.COMPLETE
            self.session.commit()
            self.update_db()
            _ = self.session.query(HazardPointValue).\
                options(subqueryload(HazardPointValue.hazardcurve).
                        subqueryload(HazardCurve.modelrun)).\
                filter(HazardModelRun.id == model_run_db.id).\
                update({HazardPointValue.modelrun_id: model_run_db.id},
                       synchronize_session=False)
            self.session.commit()
            self.update_db()

        elif self.state_evaluator(new_state, [self.error_result]):
            model_run = new_state.result
            logger.error(f"Hazard model with runid={model_run.runid}"
                         "has returned an error from the "
                         "remote worker.")
            update_model_run = self.session.query(HazardModelRun).\
                filter(HazardModelRun.id == model_run.id).first()
            update_model_run.status.state = EStatus.ERROR
            self.update_db()
        self.execution_status_update.emit((
            new_state, type(model_run),
            model_run.id))
        self.synchronous_thread.model_runs_count += 1