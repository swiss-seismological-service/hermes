# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Openquake Hazard executing related engine facilities.
"""
import sys
import yaml
from datetime import datetime
from prefect import Flow




class ModelResults(Task):
    def run(self, scenario):
        pass


class SeismicityModelResults(Task):
    def run(self, scenario):
        # Check that all enabled model runs are complete
        try:
            stage = scenario[EStage.SEISMICITY]
        except KeyError:
            raise FAIL(message=f'Scenario: {scenario} does not have a '
                    'seismicity stage, Further stages failing.', result=scenario)

        model_runs = [r for r in stage.runs if r.enabled]
        for run in model_runs:
            if run.status.state != EStatus.COMPLETE:
                raise FAIL(f'Scenario: {scenario} has model '
                           f'runs that are not complete.', result=scenario)

        for run in model_runs:
            result = run.result
            if result.samples:
                result_geom = result.geom
                result_samples = result.samples




        return seismicity_stage_done

class OQTemplates(Task):
    def run(self, oq_config_filename, forecast):
        if oq_config_filename is None:
            # There is also a catch for this in the GUI when adding
            # a scenario with hazard/risk stage.
            raise FAIL(
                message="OpenQuake configuration was not"
                "found at RAMSIS startup. Please add configuration "
                "~/.configure/SED/Ramsis/openquake_config.yml")

        self.logger = prefect.context.get('logger')
        config = self.load_oq_config(oq_config_filename,
                                     forecast.project.id)
        try:
            self.validate_paths(config)
        except FileNotFoundError:
            raise FAIL(
                message="OpenQuake configuration includes paths "
                        "or filenames that do not exist.")

    def get_forecast_results(self, forecast):
        model_results = 


        ZIP_FILENAME_BASE = 'oq_hazard_'

    
    def render_template(self, template_filename, context):
        TEMPLATE_ENVIRONMENT = Environment(
            autoescape=False,
            loader=FileSystemLoader(os.path.join(PATH)),
            trim_blocks=False)
        return TEMPLATE_ENVIRONMENT.get_template(template_filename).render(context)
    
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
    
    def validate_paths(self, config):
        template_keys = ['oq_hazard_config_file',
                         'oq_hazard_logic_tree_file',
                         'oq_hazard_model_source_template',
                         'oq_hazard_gmpe_file']
        template_dir = config['template_dir']
        inputs_dir = config['inputs_dir']
        for dir_path in [template_dir, inputs_dir]:
            if not os.path.isdir(dir_path): 
                raise FileNotFoundError("{} does not exist".format(dir_path))
        for key in template_keys:
            if not os.path.isfile(os.path.join(template_dir, config[key])):
                self.logger.error("A template file cannot be found: ", err)
                raise FileNotFoundError("{} does not exist in {}".format(
                                        config(key), template_dir))
    
