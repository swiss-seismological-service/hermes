"""
Create project based on json config. Default config
location: ./config/project.json

Usage:
python create_project -project_config config/project.json postgresql://ramsis:ramsis@localhost:5433/ramsis_res # noqa
"""

from os.path import join, dirname, abspath
import argparse
import json

from ramsis.utils import real_file_path
from ramsis.datamodel import Project, EStage

from RAMSIS.core.builder import (
    default_project, default_forecast, default_scenario)
from RAMSIS.core.store import Store
from ramsis.io.hydraulics import HYDWSBoreholeHydraulicsDeserializer

DIRPATH = dirname(abspath(__file__))


def create_scenario(project_config, scenario_config):
    scenario = default_scenario(store, name=scenario_config["SCENARIO_NAME"])
    # Seismicity Stage
    seismicity_stage = scenario[EStage.SEISMICITY]
    seismicity_stage.config = {
        'epoch_duration': scenario_config["EPOCH_DURATION"]}
    scenario.reservoirgeom = scenario_config["RESERVOIR"]
    deserializer = HYDWSBoreholeHydraulicsDeserializer(
        ramsis_proj=project_config["RAMSIS_PROJ"],
        external_proj=project_config["WGS84_PROJ"],
        ref_easting=project_config["REFERENCE_X"],
        ref_northing=project_config["REFERENCE_Y"],
        transform_func_name='pyproj_transform_to_local_coords',
        plan=True)
    with open(join(DIRPATH, scenario_config["SCENARIO_DIR"],
              scenario_config["SCENARIO_JSON"]), 'rb') as ifd:
        scenario.well = deserializer.load(ifd)

    for run in seismicity_stage.runs:
        # A model run will not be created if the model is disabled,
        # Therefore all existing model runs will be enabled.
        if project_config["RUN_MODELS"] == "ALL":
            run.enabled = True
        elif run.model.name in project_config["RUN_MODELS"]:
            run.enabled = True
        else:
            run.enabled = False

    return scenario


def create_forecast(project_config, forecast_config):

    fc = default_forecast(
        store,
        starttime=forecast_config["FORECAST_STARTTIME"],
        endtime=forecast_config["FORECAST_ENDTIME"],
        num_scenarios=0,
        name=forecast_config["FORECAST_NAME"])

    scenarios_json = forecast_config['SCENARIOS']
    scenarios = [create_scenario(project_config, scenario_config)
                 for scenario_config in scenarios_json]
    fc.scenarios = scenarios
    return fc


def create_project(store, project_config):

    project = default_project(
        name=project_config["PROJECT_NAME"],
        description=project_config["PROJECT_DESCRIPTION"],
        starttime=project_config["PROJECT_STARTTIME"],
        endtime=project_config["PROJECT_ENDTIME"],
        referencepoint_x=project_config["REFERENCE_X"],
        referencepoint_y=project_config["REFERENCE_Y"],
        proj_string=project_config["RAMSIS_PROJ"])

    project.settings['hydws_enable'] = project_config['HYDWS_ENABLE']
    project.settings['hydws_url'] = project_config['HYDWS_URL']
    project.settings['fdsnws_enable'] = project_config['FDSNWS_ENABLE']
    project.settings['fdsnws_url'] = project_config['FDSNWS_URL']

    project.forecasts = [
        create_forecast(project_config, forecast_config)
        for forecast_config in project_config["FORECASTS"]]
    store.add(project)
    project.settings.commit()
    store.save()


def parse_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'db_url', type=str, metavar='URL',
        help=('DB URL indicating the database dialect and connection '
              'arguments.'))
    parser.add_argument(
        '-project_config',
        type=real_file_path,
        default=join(DIRPATH, "config", "project.json"),
        help=("path to a json project configuration "
              "file"))

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_cli()

    store = Store(args.db_url)
    success = store.init_db()

    if success:
        pass
    else:
        print("Error, db could not be initialized: ", success)
        raise Exception("DB could not be initialized")

    projects = store.session.query(Project).all()
    project_names = [p.name for p in projects]

    with open(args.project_config, "r") as project_json:
        config = json.load(project_json)
    project_config_list = config["PROJECTS"]

    for project_config in project_config_list:
        assert project_config["PROJECT_NAME"] not in project_names, \
            "Project name already exists {project_config['PROJECT_NAME']}"

        create_project(store, project_config)
        print(f"created project {project_config['PROJECT_NAME']}")
    store.save()
    store.close()
