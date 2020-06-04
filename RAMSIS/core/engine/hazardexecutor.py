# Copyright 2018, ETH Zurich - Swiss Seismological Service SED # noqa
"""
Openquake Hazard executing related engine facilities.
"""
import os
import time
from shutil import copyfile
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm.exc import DetachedInstanceError
import prefect
from prefect.engine.signals import FAIL, LOOP
from prefect import Task
from RAMSIS.io.sfm import OQGeomSerializer
from RAMSIS.io.oq_hazard import OQHazardOMessageDeserializer, \
    OQHazardResultsListDeserializer
from RAMSIS.io.utils import TransformationError
from RAMSIS.core.worker.oq_hazard import OQHazardWorkerHandle
from ramsis.datamodel.forecast import EStage
from ramsis.datamodel.status import EStatus, Status
from ramsis.datamodel.hazard import HazardModelRun

LOGIC_TREE_BASENAME = 'logictree.xml'
GMPE_BASENAME = 'gmpe_logictree.xml'
SEISMICITY_MODEL_BASENAME = '{}_source_{}_{}.xml'
JOB_CONFIG_BASENAME = 'job.ini'
MIN_MAG = 1.0  # ALTER to come from somewhere configurable
DATETIME_FORMAT = '%Y-%m-%dT-%H-%M'


# Task which calls openquake with requests

# Task which polls oq

def render_template(template_filename, context, path):
    template_environment = Environment(
        autoescape=False,
        loader=FileSystemLoader(path),
        trim_blocks=False)
    return template_environment.get_template(
        template_filename).render(context)


class UpdateHazardRuns(Task):

    def run(self, hazard_model_run):
        new_runs = []
        for haz_run in hazard_model_run:
            self.logger = prefect.context.get('logger')
            # Assume one hazard model run per scenario
            hazard_stage = haz_run.forecaststage
            scenario = hazard_stage.scenario
            seismicity_stage = scenario[EStage.SEISMICITY]
            for seis_run in [run for run in seismicity_stage.runs
                             if run.enabled]:
                if seis_run.status.state != EStatus.COMPLETE:
                    raise FAIL(
                        message='There are non-completed seismicity model runs'
                        f' for scenario: {scenario.id}')
                seis_run.hazardruns.append(haz_run)
            new_runs.append(haz_run)
        return hazard_model_run


class OQSourceModelFiles(Task):

    def run(self, hazard_model_run, oq_input_dir):
        self.logger = prefect.context.get('logger')
        try:

            hazard_stage = hazard_model_run.forecaststage
            start = hazard_model_run.describedinterval_start
            end = hazard_model_run.describedinterval_end

            scenario = hazard_stage.scenario
            project = scenario.forecast.project
            serializer = OQGeomSerializer(
                ramsis_proj=project.spatialreference,
                ref_easting=project.referencepoint_x,
                ref_northing=project.referencepoint_y,
                transform_func_name='pyproj_transform_from_local_coords')

            seis_context = []
            for seis_run in hazard_model_run.seismicitymodelruns:
                self.validate_paths(seis_run.model, 'seismicitymodeltemplate',
                                    seis_run.model.name)
                if seis_run.status.state != EStatus.COMPLETE:
                    raise FAIL(f'Scenario: {scenario.id} has model '
                               f'runs that are not complete.', result=scenario)
                result = seis_run.result
                # Only support one level of parent-child results
                # if there are no results for a model, a model source file
                # is still created (equivalent to zero seismicity)
                geoms = []
                try:
                    children = result.children
                except DetachedInstanceError:
                    children = None

                if children:
                    for index, child_result in enumerate(children):
                        geoms = self.append_geometry(geoms, result, serializer,
                                                     start, end, index + 1)
                else:
                    geoms = self.append_geometry(geoms, result, serializer,
                                                 start, end, 1)

                xml_name = SEISMICITY_MODEL_BASENAME.format(
                    seis_run.model.name, start.strftime(DATETIME_FORMAT),
                    end.strftime(DATETIME_FORMAT))
                seis_context.append({
                    'starttime': start,
                    'endtime': end,
                    'seismicity_model_run': seis_run,
                    'model': seis_run.model,
                    'hazard_weighting': seis_run.weight,
                    'xml_name': xml_name,
                    'geometries': geoms,
                    'min_mag': MIN_MAG})

            source_models = []
            for model_context in seis_context:
                # Call xml writer
                template_filename = model_context['seismicity_model_run'].\
                    model.seismicitymodeltemplate
                with open(
                    os.path.join(oq_input_dir,
                                 model_context['xml_name']), 'w') as model_file:
                    model_file.write(render_template(
                        os.path.basename(template_filename),
                        model_context,
                        os.path.dirname(template_filename)))
                    source_models.append(
                        (model_context['xml_name'],
                         model_context['seismicity_model_run'].weight))
        except Exception as err:

            self.logger.error("Get model files failed: ", err)
            scenario = hazard_model_run.forecaststage.scenario
            raise FAIL(f'Scenario: {scenario.id} has model '
                       f'runs that are not complete.', result=scenario)
        return source_models

    def append_geometry(self, geoms, result, serializer, start, end, geom_id):
        sample = result.matching_timeperiod(start, end)
        if sample:
            linearring = self.create_geom(result, serializer)
            geoms.append((geom_id, sample, linearring))
        return geoms

    def create_geom(self, result, serializer):
        logger = prefect.context.get('logger')
        if not result.samples:
            logger.info(
                "There are no forecast values stored for the result "
                f"area: x_min: {result.x_min}, x_max: {result.x_max}, y_min: "
                f"{result.y_min}, y_max: {result.y_max}."
                f" seismicitypredictionbin.id: {result.id}.")
            return
        try:
            snapshot_result = result.snapshot()
            result = serializer.dumps(snapshot_result)
            return result.get('linearring')
        except (KeyError, TransformationError) as err:
            raise FAIL(
                message=f"OQ Hazard model result {result.id} does not"
                " contain all the information required to form a linear "
                f"ring. {err}")

    def validate_paths(self, obj_name, attr_name, model_name):

        template = getattr(obj_name, attr_name)
        if template is None:
            raise FAIL(
                message=("OpenQuake configuration was not "
                         "added for the hazard stage in the seismicity model. "
                         f"{obj_name} {attr_name} {model_name}"))
        if not os.path.isfile(template):
            raise FAIL(
                message=("OpenQuake template does not exist for model "
                         f"{model_name}: {template}"))


class CreateHazardModelRunDir(Task):

    def run(self, data_dir, hazard_model_run):
        scenario = hazard_model_run.forecaststage.scenario
        project = scenario.forecast.project

        project_name = project.name.replace(" ", "")
        project_dir = os.path.join(
            data_dir, f"ProjectId_{project.id}_{project_name}")
        if not os.path.isdir(project_dir):
            os.mkdir(project_dir)

        scenario_name = scenario.name.replace(" ", "")
        scenario_dir = os.path.join(
            project_dir, f"ForecastScenarioId_{scenario.id}_{scenario_name}")
        if not os.path.isdir(scenario_dir):
            os.mkdir(scenario_dir)

        # create the hazard level files
        starttime = hazard_model_run.describedinterval_start
        endtime = hazard_model_run.describedinterval_end
        hazard_dir = os.path.join(
            scenario_dir, f"HazardModelRunId_{hazard_model_run.id}_"
            f"{starttime.strftime(DATETIME_FORMAT)}_"
            f"{endtime.strftime(DATETIME_FORMAT)}")
        if not os.path.isdir(hazard_dir):
            os.mkdir(hazard_dir)
        return hazard_dir


class OQFiles(Task):
    def run(self, hazard_model_run, oq_input_dir):
        hazard_model = hazard_model_run.model
        for attr_name in [
                'logictreetemplate',
                'jobconfigfile',
                'gmpefile']:
            self.validate_paths(hazard_model, attr_name)

        # Copy the job config and the gmpe file over.

        gmpe_filename = os.path.join(oq_input_dir, GMPE_BASENAME)
        open(gmpe_filename, 'w').close()
        copyfile(hazard_model.gmpefile, gmpe_filename)

        job_filename = os.path.join(oq_input_dir, JOB_CONFIG_BASENAME)
        open(job_filename, 'w').close()
        copyfile(hazard_model.jobconfigfile, job_filename)

    def validate_paths(self, obj_name, attr_name):

        template = getattr(obj_name, attr_name)
        if template is None:
            raise FAIL(
                message=(
                    "OpenQuake configuration was not"
                    f"added for the hazard stage. {obj_name} {attr_name}"))
        if not os.path.isfile(template):
            raise FAIL(
                message=f"OpenQuake template does not exist: {template}")


class CreateHazardModelRuns(Task):
    """
    Prefect task that creates hazard model runs based
    on the results on the seismicity forecast stage.
    Each sesimicity forecast time interval contains different
    numerical results and so must have a seperate openquake run.
    """
    def run(self, scenario):
        hazard_stage = scenario[EStage.HAZARD]
        seismicity_stage = scenario[EStage.SEISMICITY]
        result_times = seismicity_stage.result_times
        hazard_model_runs = []
        for starttime, endtime in result_times:
            haz_run = HazardModelRun(
                describedinterval_start=starttime,
                describedinterval_end=endtime,
                model=hazard_stage.model,
                status=Status(),
                # need to access the seismicitymodelruns attribute
                # so it is loaded
                seismicitymodelruns=[],
                enabled=True)
            hazard_model_runs.append(haz_run)
        hazard_stage.runs = hazard_model_runs
        return hazard_model_runs


class OQLogicTree(Task):
    """
    Prefect task to create a logic tree file which references
    all the model source files. The directory containing inputs
    to the openquake hazard run stage will then be complete, so the
    directory is zipped.
    """
    def normalize_model_weights(self, model_sources):
        normalized_model_sources = []
        cumulated_weight = 0.0

        total_weight = sum(weight for model_source, weight in model_sources)
        for index, source in enumerate(model_sources):
            source_name, weight = source
            if index == len(model_sources) - 1:
                new_weight = 1.0 - cumulated_weight
            else:
                new_weight = round(weight / total_weight, 2)
                cumulated_weight += new_weight
            normalized_model_sources.append((source_name, new_weight))
        return normalized_model_sources

    def run(self, hazard_model_run, oq_input_dir, model_sources):
        hazard_model = hazard_model_run.model

        template_filename = hazard_model.logictreetemplate
        normalized_model_sources = self.normalize_model_weights(model_sources)

        logic_tree_context = {'model_sources':
                              normalized_model_sources}
        logic_tree_filename = os.path.join(oq_input_dir, LOGIC_TREE_BASENAME)
        with open(logic_tree_filename, 'w') as logic_tree_file:
            rendered_xml = render_template(os.path.basename(template_filename),
                                           logic_tree_context,
                                           os.path.dirname(template_filename))
            logic_tree_file.write(rendered_xml)

        return logic_tree_filename


class OQHazardModelRunExecutor(Task):
    """
    The executor instantiates the actual model that is associated with the run,
    connects to its status update signal and then calls its run method.
    """
    TASK_ACCEPTED = 'created'

    def run(self, model_runs, source_filenames_for_runs, oq_dirs):
        for (run, source_filenames, oq_dir) in zip(
                model_runs, source_filenames_for_runs, oq_dirs):
            _worker_handle = OQHazardWorkerHandle.from_run(run)

            try:
                resp = _worker_handle.compute(
                    JOB_CONFIG_BASENAME, LOGIC_TREE_BASENAME,
                    GMPE_BASENAME, source_filenames, oq_dir)
            except OQHazardWorkerHandle.RemoteWorkerError:
                raise FAIL(
                    message="model run submission has failed with "
                    "error: RemoteWorkerError. Check if remote worker is"
                    " accepting requests.",
                    result=run)

            status = resp['status']

            if status != self.TASK_ACCEPTED:
                raise FAIL(message=f"model run {resp['id']} "
                           f"has returned an error: {resp}", result=run)

            run.runid = resp['job_id']
            # Next task requires knowledge of status, so update status
            # inside task.
            run.status.state = EStatus.DISPATCHED
        return model_runs


class OQHazardModelRunPoller(Task):
    """
    Executes a single openquake hazard model run

    The executor instantiates the actual model that is associated with the run,
    connects to its status update signal and then calls its run method.
    """
    TASK_PROCESSING = ['created', 'submitted', 'executing']
    TASK_COMPLETE = 'complete'
    TASK_ERROR = ['aborted', 'failed', 'deleted']

    def run(self, forecast, model_run, session):
        """
        :param run: Model run to execute
        :type run: :py:class:`ramsis.datamodel.seismicity.HazardModelRun`
        """
        logger = prefect.context.get('logger')
        logger.debug(f"Polling for runid={model_run.runid}")
        _worker_handle = OQHazardWorkerHandle.from_run(
            model_run)

        try:
            query_response = _worker_handle.query(
                model_run.runid).first()

        except OQHazardWorkerHandle.RemoteWorkerError as err:
            logger.error(str(err))
            raise FAIL(result=model_run)

        status = query_response["status"]
        if status in self.TASK_ERROR:
            raise FAIL(
                message="Hazard Model Worker"
                " has returned an unsuccessful status code."
                f"(runid={model_run.runid}: {query_response})",
                result=model_run)
        elif status in self.TASK_PROCESSING:
            logger.info("sleeping")
            time.sleep(15)
            raise LOOP(
                message=f"(forecast{forecast.id})(scenario.id="
                f"{model_run.forecaststage.scenario}) "
                f"(runid={model_run.runid}): Polling")
        else:
            # Get list of results available matching htypes
            results_deserializer = OQHazardResultsListDeserializer()
            results_list = _worker_handle.query_results(
                model_run.runid, deserializer=results_deserializer).all()
            deserializer = OQHazardOMessageDeserializer(
                session=session)
            logger.info(
                f'OQ has results for (run={model_run!r}, '
                f'runid={model_run.runid}): {results_list}')
            results = []
            for result in results_list:
                try:
                    result_resp = _worker_handle.query_result_file(
                        result,
                        deserializer=deserializer).all()
                    results.append(result_resp)
                except OQHazardWorkerHandle.RemoteWorkerError as err:
                    logger.error(str(err))
                    raise FAIL(model_run)
            return model_run, results
