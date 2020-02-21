# Copyright 2018, ETH Zurich - Swiss Seismological Service SED # noqa
"""
Openquake Hazard executing related engine facilities.
"""
import os
from shutil import copyfile
from zipfile import ZipFile
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import inspect
from sqlalchemy.orm.exc import DetachedInstanceError
import prefect
from prefect.engine.signals import FAIL
from prefect import Task
from RAMSIS.io.sfm import OQGeomSerializer
from RAMSIS.io.utils import TransformationError
from ramsis.datamodel.forecast import EStage
from ramsis.datamodel.status import EStatus, Status
from ramsis.datamodel.hazard import HazardModelRun

LOGIC_TREE_BASENAME = 'logictree.xml'
GMPE_BASENAME = 'gmpe_logictree.xml'
SEISMICITY_MODEL_BASENAME = '{}__source_{}_{}.xml'
JOB_CONFIG_BASENAME = 'job.ini'
MIN_MAG = 1.0 # ALTER


class ModelResults(Task):
    def run(self, scenario):
        pass


def render_template(template_filename, context, path):
    template_environment = Environment(
        autoescape=False,
        loader=FileSystemLoader(path),
        trim_blocks=False)
    return template_environment.get_template(template_filename).render(context)


class UpdateHazardRuns(Task):

    def run(self, hazard_model_run):
        self.logger = prefect.context.get('logger')
        # Assume one hazard model run per scenario
        hazard_stage = hazard_model_run.forecaststage
        scenario = hazard_stage.scenario
        seismicity_stage = scenario[EStage.SEISMICITY]
        for seis_run in [run for run in seismicity_stage.runs if run.enabled]:
            if seis_run.status.state != EStatus.COMPLETE:
                raise FAIL(message='There are non-completed seismicity model runs'
                           f' for scenario: {scenario.id}')
            seis_run.hazardruns.append(hazard_model_run)

        #hazard_model_run.seismicitymodelruns = seismicity_model_runs
        return hazard_model_run

class OQSourceModelFiles(Task):

    def run(self, hazard_model_run, oq_input_dir):
        print("oq source models: ", hazard_model_run.id, hazard_model_run.seismicitymodelruns)
        self.logger = prefect.context.get('logger')
        # Assume one hazard model run per scenario
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
            geoms = []
            try:
                children = result.children
            except DetachedInstanceError:
                children = None
            if children:
                for child_result in children:
                    sample = child_result.matching_timeperiod(start, end)
                    if sample:
                        linearring = self.create_geom(child_result, serializer)
                        geoms.append((sample, linearring))
            else:
                sample = result.matching_timeperiod(start, end)
                if sample:
                    linearring = self.create_geom(result, serializer)
                    geoms.append((sample, linearring))

            xml_name = SEISMICITY_MODEL_BASENAME.format(
                    seis_run.model.name, start, end)
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
            #samples = [result.matching_timeperiod(start, end) for
            #           result, linearring in model_context['geometries']]
            #model_context['samples'] = samples

            # call xml writer
            template_filename = model_context['seismicity_model_run'].model.seismicitymodeltemplate
            with open(os.path.join(oq_input_dir,
                                   model_context['xml_name']), 'w') as model_file:
                model_file.write(render_template(
                    os.path.basename(template_filename),
                    model_context,
                    os.path.dirname(template_filename)
                    ))
                source_models.append((model_context['xml_name'],
                                      model_context['seismicity_model_run'].weight))
        return source_models

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
            result = serializer.dumps(result)
            return result.get('linearring')
        except (KeyError, TransformationError) as err:
            raise FAIL(
                message=f"Seismicity model result {result.id} does not"
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
        str_format = '%Y-%m-%dT-%H-%M'
        starttime = hazard_model_run.describedinterval_start
        endtime = hazard_model_run.describedinterval_end
        hazard_dir = os.path.join(
            scenario_dir, f"HazardModelRunId_{hazard_model_run.id}_"
            f"{starttime.strftime(str_format)}_"
            f"{endtime.strftime(str_format)}")
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
        copyfile(hazard_model.jobconfigfile, gmpe_filename)

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
            session = inspect(haz_run).session
        hazard_stage.runs = hazard_model_runs
        return hazard_model_runs



class OQLogicTree(Task):
    def run(self, hazard_model_run, oq_input_dir, model_sources):
        print("oq_input dir", oq_input_dir)
        hazard_model = hazard_model_run.model

        template_filename = hazard_model.logictreetemplate
        print("logictree template", template_filename)
        weighted_model_sources = []
        total_weight = sum(weight for model_source, weight in model_sources)
        cumulated_weight = 0.0
        for index, source in enumerate(model_sources):
            source_name, weight = source
            if index == len(model_sources) - 1:
                new_weight = 1.0 - cumulated_weight
            else:
                new_weight = round(weight / total_weight, 2)
                cumulated_weight += new_weight
            weighted_model_sources.append((source_name, new_weight))


        logic_tree_context = {'model_sources':
                              weighted_model_sources}
        logic_tree_filename = os.path.join(oq_input_dir, LOGIC_TREE_BASENAME)
        with open(logic_tree_filename, 'w') as logic_tree_file:
            rendered_xml = render_template(os.path.basename(template_filename),
                                           logic_tree_context,
                                           os.path.dirname(template_filename))
            logic_tree_file.write(rendered_xml)

        zipfile_name = f"{oq_input_dir}.zip"
        with ZipFile(zipfile_name, 'w') as oq_zipfile:
            oq_basenames = os.listdir(oq_input_dir)
            for basename in oq_basenames:
                pass
                #oq_zipfile.write(os.path.join(oq_input_dir, basename))
        
        return hazard_model_run, zipfile_name 
