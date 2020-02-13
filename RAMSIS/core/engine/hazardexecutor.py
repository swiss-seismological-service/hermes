# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Openquake Hazard executing related engine facilities.
"""
import sys
import yaml
from datetime import datetime
from prefect import Flow
from RAMSIS.io.sfm import OQGeomSerializer
from RAMSIS.io.utils import TransformationError

LOGIC_TREE_BASENAME = 'logictree.xml'
GMPE_BASENAME = 'gmpe_logictree.xml'
SEISMICITY_MODEL_BASENAME = '{}_source_{}.xml'
JOB_CONFIG_BASENAME = 'job.ini'


class ModelResults(Task):
    def run(self, scenario):
        pass


class SeismicityModelResults(Task):
    def serialize_function(self, result, serializer):
        try:
            linearring = serializer.dumps(result)['linearring']
        except KeyError, TransformationError as err:
          raise FAIL(message=f"Seismicity model result {result.id} does not"
                     " contain all the information required to form a linear "
                     f"ring. {err}")  
          return linearring
        

    def run(self, scenario, oq_input_dir):
        self.logger = prefect.context.get('logger')
        # Check that all enabled model runs are complete
        try:
            seismicity_stage = scenario[EStage.SEISMICITY]
        except KeyError:
            raise FAIL(message=f'Scenario: {scenario} does not have a '
                    'seismicity stage, Further stages failing.', result=scenario)
        seismicity_model_runs = [r for r in stage.runs if r.enabled]
        hazard_model_run.seismicitymodelruns = seismicity_model_runs
        project = scenario.forecast.project
        serializer = OQGeomSerializer(
            ramsis_proj=project.spatialreference,
            ref_easting=project.referencepoint_x,
            ref_northing=project.referencepoint_y,
            transform_func_name='pyproj_transform_from_local_coords')
        seis_context = []
        for seis_run in seismicity_model_runs:
            self.validate_paths(seis_run.model, 'seismicitymodeltempalate', info=seis_run.model.name):
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

        source_xml_names = []
        for starttime, endtime in distinct_dates:
            xml_basename = f"{starttime}_{endtime}_source_models.xml"
            time_context = []
            for model_context in seis_context:
                samples = [result.sample_matching_timeperiod(starttime, endtime) for result, linearring in model_context['geometries']
                time_context.append({**model_context, **{'samples': samples}}) 
            # call xml writer
                
                        

     
                     
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
        except KeyError, TransformationError as err:
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
@task
def create_oq_dir(data_dir, system_time, hazard_model_run):
    # create the hazard level files
    oq_input_dir = os.path.join(data_dir, "hazard_run_{hazard_model_run.id}_{system_time}") 
    return oq_input_dir


class OQTemplates(Task):
    def run(self, scenario, oq_input_dir, seismicity_source_filenames):
        # Should there be only one hazard model run per scenario?
        hazard_model_run = scenario.EStage[HAZARD].runs[0]


        hazard_model = hazard_model_run.model
        for attr_name in [
                'logictreetemplate',
                'jobconfigtemplate',
                'gmpetemplate']:
            self.validate_paths(hazard_model, attr_name)

 
        logic_tree_context = {'seismicity_source_names': seismicity_source_names}
        logic_tree_template_filename = getattr(hazard_model, 'logictreetemplate')
        logic_tree_filename = os.path.join(oq_input_dir, LOGIC_TREE_BASENAME)
        with open(logic_tree_filename, 'w') as logic_tree_file:
            html = self.render_template(logic_tree_template_filename, logic_tree_context)
            logic_tree_file.write(html)

        gmpe_context = {}
        gmpe_template_filename = getattr(hazard_model, 'gmpetemplate')
        gmpe_filename = os.path.join(oq_input_dir, GMPE_BASENAME)
        with open(gmpe_filename, 'w') as gmpe_file:
            html = self.render_template(logic_tree_template_filename, logic_tree_context)
            gmpe_file.write(html)

        job_context = {}
        job_template_filename = getattr(hazard_model, 'jobconfigtemplate')
        job_filename = os.path.join(oq_input_dir, JOB_CONFIG_BASENAME)
        with open(logic_tree_filename, 'w') as job_config_file:
            html = self.render_template(job_config_template_filename, job_config_context)
            job_config_file.write(html)

        zipfile_name = f"{oq_input_dir}.zip"
        with ZipFile(zipfile_name, 'w') as oq_zipfile:
            oq_basenames = os.listdir(oq_input_dir)
            for basename in oq_basename:
                oq_zipfile.write(os.path.join(oq_input_dir, basename))
        
        return hazard_model_run, zipfile_name 
    

    def render_template(self, template_filename, context):
        template_environment = Environment(
            autoescape=False,
            loader=FileSystemLoader(os.path.join(PATH)),
            trim_blocks=False)
        return template_environment.get_template(template_filename).render(context)
    
    def create_input_files(self, config):
        subgeom1 = {'id': 1, 'a_value': 2.4, 'b_value': 3.1, 'mc_value': 10.0, 'min_mag': 1.0, 'linear_ring_positions': '-5.0000000E-01 -5.0000000E-01 -3.0000000E-01 -1.0000000E-01 1.0000000E-01 2.0000000E-01 3.0000000E-01 -8.0000000E-01'}
        subgeom2 = {'id': 2, 'a_value': 2.0, 'b_value': 3.5, 'mc_value': 10.0, 'min_mag': 1.0, 'linear_ring_positions': '-15.0000000E-01 -15.0000000E-01 -13.0000000E-01 -11.0000000E-01 11.0000000E-01 12.0000000E-01 13.0000000E-01 -18.0000000E-01'}
        seismicity_model_runs = [{'name': 'EM1.1', 'hazard_weighting': 0.3, "xml_filename": "em1_source_1234.xml"},
                {'model_name': 'EM1.2', 'hazard_weighting': 0.7, "xml_filename": "em1_source_1235.xml"}]
        for model in seismicity_model_runs:
            source_fname = model['xml_filename']
            context_model_tree = {'model': [model], 'geometries': [subgeom1, subgeom2]}
            source_template_file = 'area_source_template.txt'
    
            with open(os.path.join(PATH, source_fname), 'w') as f:
                html = render_template(source_template_file, context_model_tree)
                f.write(html)
    
        logic_tree_fname = "logic_tree_model_sources.xml"
        context_logic_tree = {'seismicity_model_runs': seismicity_model_runs}
        logic_template_file = 'model_sources_logic_tree_template.xml'
    
        with open(os.path.join(PATH, logic_tree_fname), 'w') as f:
            html = render_template(logic_template_file, context_logic_tree)
            f.write(html)


    # Check that paths defined in config exist
    def load_oq_config(self, oq_config_filename, project_id):
        with open(oq_config_filename, 'r') as conf:
            oq_config = yaml.full_load(conf.read())
        default_config = oq_config['default_configuration']
        proj_config = None
        if 'projects' in oq_config.keys():
            for proj in oq_config['projects']:
                if proj['database_id'] == project_id:
                    proj_config = proj
    
        if not proj_config:
            self.logger.info("No project specific OpenQuake configuration exists."
                             " Using default configuration.")
            config = default_config
        else:
            config = {**default_config, **proj_config}
        return config
    
    def validate_paths(self, obj_name, attr_name):
       
        template = getattr(obj_name, attr_name)
        if template is None:
            raise FAIL(
                message=("OpenQuake configuration was not"
                         f"added for the hazard stage. {obj_name} {attr_name}"))
        if not os.path.isfile(template):
            raise FAIL(
                message=f"OpenQuake template does not exist: {template}")
    
