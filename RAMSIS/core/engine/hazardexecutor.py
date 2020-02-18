# Copyright 2018, ETH Zurich - Swiss Seismological Service SED # noqa
"""
Openquake Hazard executing related engine facilities.
"""
import os
import sys
import yaml
from shutil import copyfile
from datetime import datetime
import prefect

from prefect import Task, task
from RAMSIS.io.sfm import OQGeomSerializer
from RAMSIS.io.utils import TransformationError

LOGIC_TREE_BASENAME = 'logictree.xml'
GMPE_BASENAME = 'gmpe_logictree.xml'
SEISMICITY_MODEL_BASENAME = '{}_source_{}.xml'
JOB_CONFIG_BASENAME = 'job.ini'


class ModelResults(Task):
    def run(self, scenario):
        pass


def render_template(self, template_filename, context, path):
    template_environment = Environment(
        autoescape=False,
        loader=FileSystemLoader(path),
        trim_blocks=False)
    return template_environment.get_template(template_filename).render(context)


class OQSourceModelFiles(Task):
    def serialize_function(self, result, serializer):
        try:
            linearring = serializer.dumps(result)['linearring']
        except (KeyError, TransformationError) as err:
            raise FAIL(message=f"Seismicity model result {result.id} does not"
                       " contain all the information required to form a linear "
                       f"ring. {err}")  
        return linearring
        

    def run(self, hazard_model_run, oq_input_dir):
        self.logger = prefect.context.get('logger')
        # Assume one hazard model run per scenario
        hazard_stage = scenario[EStage.HAZARD]
        if len(hazard_stage.runs) != 1:
            raise FAIL(message="More than one hazard stage configured in scenario")
        scenario = hazard_model_run.scenario
        # Check that all enabled model runs are complete
        try:
            seismicity_stage = scenario[EStage.SEISMICITY]

        except KeyError:
            raise FAIL(message=f'Scenario: {scenario} does not have a '
                    'seismicity stage, Further stages failing.', result=scenario)
        seismicity_model_runs = [r for r in stage.runs if r.enabled]
        if not all(r.status.state==EStatus.COMPLETE for r in seismicity_model_runs):
            raise FAIL(message="Seismicity model runs for scenario: "
                       f"{scenario} do not have a state of EStatus.COMPLETE")
        hazard_model_run.seismicitymodelruns = seismicity_model_runs
        project = scenario.forecast.project
        serializer = OQGeomSerializer(
            ramsis_proj=project.spatialreference,
            ref_easting=project.referencepoint_x,
            ref_northing=project.referencepoint_y,
            transform_func_name='pyproj_transform_from_local_coords')
        seis_context = []
        for seis_run in seismicity_model_runs:
            self.validate_paths(seis_run.model, 'seismicitymodeltempalate', info=seis_run.model.name)
            if seis_run.status.state != EStatus.COMPLETE:
                raise FAIL(f'Scenario: {scenario.id} has model '
                           f'runs that are not complete.', result=scenario)
            result = seis_run.result
            # Only support one level of parent-child results
            distinct_dates = seis_run.result_times()
            geoms = []
            if result.children:
                for child_result in children:
                    linearring = self.create_geom(child_result)
                    if linearring:
                        geoms.append((child_result, linearring))
            else:
                linearring = self.create_geom(result)
                if linearring:
                    geoms.append((result, linearring))

            seis_context.append({
                'name': seis_run.model.name,
                'hazard_weighting': seis_run.weight,
                'xml_basename': f"{seis_run.model.name}_{seis_run.id}",
                'geometries': geoms})

        xml_names = []
        for starttime, endtime in distinct_dates:
            xml_basename = f"{starttime}_{endtime}_source_models.xml"
            time_context = []
            for model_context, seis_model in zip(seis_context, seismicity_model_runs):
                samples = [result.sample_matching_timeperiod(starttime, endtime) for result, linearring in model_context['geometries']]
                time_context.append({**model_context, **{'samples': samples}}) 
            # call xml writer
            with open(os.path.join(oq_input_dir, SEISMICITY_MODEL_BASENAME), 'w') as model_file:
                model_file.write(render_template(seis_model.model.seismicitymodeltemplate))
                xml_names.append(SEISMICITY_MODEL_BASENAME) 
        return xml_names
                     
    def create_geom(self, result):
        logger = prefect.context.get('logger')
        if not result.samples:
            logger.info("There are no forecast values stored for the result "
                        f"area: x_min: {result.x_min}, x_max: {x_max}, y_min: "
                        f"{result.y_min}, y_max: {result.y_max}."
                        f" seismicitypredictionbin.id: {result.id}.")
            return
        try:
            return serializer.dumps(result)['linearring']
        except (KeyError, TransformationError) as err:
          raise FAIL(message=f"Seismicity model result {result.id} does not"
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



        return seismicity_stage_done

class CreateOQDir(Task):

    def run(self, data_dir, system_time, hazard_model_run):
        # create the hazard level files
        oq_input_dir = os.path.join(data_dir, f"hazard_run_{hazard_model_run.id}_{system_time.strftime('%Y-%m-%dT%H:%M')}") 
        return oq_input_dir


class OQFiles(Task):
    def run(self, hazard_model_run, oq_input_dir):
        hazard_model = hazard_model_run.model
        for attr_name in [
                'logictreetemplate',
                'jobconfigfile',
                'gmpefile']:
            self.validate_paths(hazard_model, attr_name)

        # Copy the job config and the gmpe file over.
        
        gmpe_context = {}
        print("inputs OQFiles", oq_input_dir, GMPE_BASENAME)
        gmpe_filename = os.path.join(oq_input_dir, GMPE_BASENAME)
        open(gmpe_filename, 'w').close()
        copyfile(hazard_model.gmpefile, gmpe_filename)

        job_context = {}
        job_filename = os.path.join(oq_input_dir, JOB_CONFIG_BASENAME)
        open(job_filename, 'w').close()
        copyfile(hazard_model.jobconfigfile, gmpe_filename)
 
    def validate_paths(self, obj_name, attr_name):
       
        template = getattr(obj_name, attr_name)
        if template is None:
            raise FAIL(
                message=("OpenQuake configuration was not"
                         f"added for the hazard stage. {obj_name} {attr_name}"))
        if not os.path.isfile(template):
            raise FAIL(
                message=f"OpenQuake template does not exist: {template}")
    
class OQLogicTree(Task):
    def run(self, model_run, oq_input_dir, source_model_xml_basenames):
        hazard_model = hazard_model_run.model
 
        logic_tree_context = {'seismicity_source_names': source_model_xml_basenames}
        logic_tree_template_filename = hazard_model.logictreetemplate
        logic_tree_filename = os.path.join(oq_input_dir, LOGIC_TREE_BASENAME)
        with open(logic_tree_filename, 'w') as logic_tree_file:
            rendered_xml = render_template(logic_tree_template_filename, logic_tree_context)
            logic_tree_file.write(rendered_xml)


        zipfile_name = f"{oq_input_dir}.zip"
        with ZipFile(zipfile_name, 'w') as oq_zipfile:
            oq_basenames = os.listdir(oq_input_dir)
            for basename in oq_basename:
                oq_zipfile.write(os.path.join(oq_input_dir, basename))
        
        return hazard_model_run, zipfile_name 
