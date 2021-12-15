"""
Bootstrap the Bedretto 2020 Nov data projects
"""
import os
from os.path import join
import argparse

from datetime import datetime

from ramsis.datamodel.forecast import (  # noqa
    Forecast, ForecastScenario, ForecastStage, SeismicityForecastStage,
    SeismicitySkillStage, HazardStage, RiskStage, EStage)
from ramsis.datamodel.hydraulics import (  # noqa
    Hydraulics, InjectionPlan, HydraulicSample)
from ramsis.datamodel.model import Model, ModelRun  # noqa
from ramsis.datamodel.project import Project  # noqa
from ramsis.datamodel.seismicity import (  # noqa
    SeismicityModel, SeismicityModelRun, ReservoirSeismicityPrediction,
    SeismicityPredictionBin)
from ramsis.datamodel.hazard import HazardModel
from ramsis.datamodel.seismics import SeismicCatalog, SeismicEvent  # noqa
from ramsis.datamodel.settings import ProjectSettings  # noqa
from ramsis.datamodel.status import Status  # noqa
from ramsis.datamodel.well import InjectionWell, WellSection  # noqa
from ramsis.datamodel.model import EModel  # noqa

from RAMSIS.core.builder import (
    default_project, default_forecast, default_scenario)
from RAMSIS.core.store import Store
from ramsis.io.hydraulics import HYDWSBoreholeHydraulicsDeserializer
from ramsis.io.seismics import QuakeMLObservationCatalogDeserializer

DIRPATH = os.path.dirname(os.path.abspath(__file__))
DIR_HYDRAULICS = "hyd"

DIR_SEISMICS = "seismics"
PATH_SEISMICS = "catalog_em1.qml"

PATH_SCENARIO = "scenario_st2_section_5_20.json"
PROJECT_STARTTIME_1 = datetime(2020, 11, 24, 13, 0)
PROJECT_ENDTIME_1 = datetime(2020, 11, 26, 0, 0)

FORECAST_STARTTIME_1 = datetime(2020, 11, 25, 4, 0)
FORECAST_ENDTIME_1 = datetime(2020, 11, 25, 22, 50)

# autopep8: off

RESERVOIR = {"x": [2679355.36334284, 2679655.36334284],
             "y": [1151313.82210478, 1151613.82210478],
             "z": [1122.33103153, 1422.33103153]}

# autopep8: on

RAMSIS_PROJ = "epsg:2056"
WGS84_PROJ = "epsg:4326"
# use the 0 point of the swiss grid as the reference point.
REFERENCE_X = 0.0
REFERENCE_Y = 0.0


def create_models():
    path_templates = "/home/sarsonl/repos/em1/rt-ramsis/oq_templates_bootstrap"
    URL_EM1 = "http://localhost:5000"#'http://ramsis-em1'
    MODEL_PARAMS = {"Tau": 60, "dM": 0.02, "Mc": None,
                    "tau_force": False, "mode": "MLE", "Nsim": 100}
    WRAPPER_PARAMS = {"well_section_publicid": "smi:ch.ethz.sed/bh/ST2/section_05_20",
            "reference_point": [2679505.3633428435, 1151463.8221047814, 1272.33103152695]}
    CONFIG = {"model_parameters": MODEL_PARAMS, "wrapper_parameters": WRAPPER_PARAMS }
    EM1_SFMWID = 'em1'

    SEISMICITY_MODEL_TEMPLATE = \
        f"{path_templates}/single_reservoir_seismicity_template.xml"

    # NOTE(sarsonl): "em1_training_epoch_duration" is optional and defaults to
    # None in the model if not provided. This means the model trains for the
    # maximum length of time possible from data provided, which is the time
    # between first and last hydraulic sample with with positive topflow.

    retval = []

    m = SeismicityModel(
        name='EM1-MLE',
        config=CONFIG,
        sfmwid=EM1_SFMWID,
        enabled=True,
        url=URL_EM1,
        seismicitymodeltemplate=SEISMICITY_MODEL_TEMPLATE)
    retval.append(m)

    # add hazard model
    m = HazardModel(
        name='hazard-model',
        enabled=True,
        logictreetemplate=os.path.join(path_templates,
                                       "logic_tree_template.xml"),
        jobconfigfile=os.path.join(path_templates, "job.ini"),
        gmpefile=os.path.join(path_templates, "gmpe_file.xml"),
        url="http://bedretto-events.ethz.ch/fdsnws")
    retval.append(m)

    return retval

def create_bedretto_25_nov_project(store):
    # FIXME(damb): TheV project and deserializers are configured without any
    # srid. As a consequence, no transformation is performed when importing
    # data.

    # import seismic catalog
    deserializer = QuakeMLObservationCatalogDeserializer(
        ramsis_proj=RAMSIS_PROJ,
        external_proj=WGS84_PROJ,
        ref_easting=REFERENCE_X,
        ref_northing=REFERENCE_Y,
        transform_func_name='pyproj_transform_to_local_coords')

    with open(join(DIRPATH, DIR_SEISMICS, PATH_SEISMICS), 'rb') as ifd:
        cat = deserializer.load(ifd)

    # create project
    project_1 = default_project(
        name='Bedretto 2020 25th Nov',
        description='Bedretto project 25th Nov',
        starttime=PROJECT_STARTTIME_1,
        endtime=PROJECT_ENDTIME_1,
        proj_string=RAMSIS_PROJ,
        referencepoint_x=REFERENCE_X,
        referencepoint_y=REFERENCE_Y)

    project_1.seismiccatalog = cat
    store.add(project_1)

    store.save()
    project_1.settings['hydws_enable'] = True
    project_1.settings['hydws_url'] = "http://inducat.ethz.ch:8080/hydws/v1/boreholes/c21pOmNoLmV0aHouc2VkL2JoL1NUMg==?level=hydraulic"

    project_1.settings['fdsnws_enable'] = True
    project_1.settings['fdsnws_url'] = "http://inducat.ethz.ch:8081/fdsnws/event/1/query?contributor=GES202111"
    project_1.settings.commit()
    store.save()
    # create forecast
    fc_1 = default_forecast(store, starttime=FORECAST_STARTTIME_1,
                            endtime=FORECAST_ENDTIME_1,
                            num_scenarios=0,
                            name='Bedretto Forecast default')

    # add exemplary scenario
    fc_1.project = project_1
    scenario_1 = default_scenario(store, name='Bedretto Scenario 1, 30 mins')
    fc_1.scenarios = [scenario_1]
    seismicity_stage = scenario_1[EStage.SEISMICITY]
    seismicity_stage.config = {'epoch_duration': 1800}
    scenario_1.reservoirgeom = RESERVOIR
    deserializer = HYDWSBoreholeHydraulicsDeserializer(
        ramsis_proj=RAMSIS_PROJ,
        external_proj=WGS84_PROJ,
        ref_easting=REFERENCE_X,
        ref_northing=REFERENCE_Y,
        transform_func_name='pyproj_transform_to_local_coords',
        plan=True)

    hazard_stage = scenario_1[EStage.HAZARD]
    hazard_models = store.load_models(model_type=EModel.HAZARD)
    hazard_stage.model = hazard_models[0]
    with open(join(DIRPATH, DIR_HYDRAULICS, PATH_SCENARIO), 'rb') as ifd:
        scenario_1.well = deserializer.load(ifd)
    store.add(fc_1)
    store.add(scenario_1)

def parse_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'db_url', type=str, metavar='URL',
        help=('DB URL indicating the database dialect and connection '
              'arguments.'))

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_cli()

    store = Store(args.db_url)
    success = store.init_db()
    if success:
        print("New db initialized")
    else:
        print("Error, db could not be initialized: ", success)
        raise Exception("DB could not be initialized")

    projects = store.session.query(Project).all()
    project_names = [p.name for p in projects]
    #assert 'Bedretto 2020 25th Nov' not in project_names, \
    #    "Project name already exists"

    # import first file in hydraulics list.
    deserializer = HYDWSBoreholeHydraulicsDeserializer(
        ramsis_proj=RAMSIS_PROJ,
        external_proj=WGS84_PROJ,
        ref_easting=REFERENCE_X,
        ref_northing=REFERENCE_Y,
        transform_func_name='pyproj_transform_to_local_coords')

    seis_models_db = store.session.query(SeismicityModel).all()
    haz_models_db = store.session.query(HazardModel).all()
    print(f"The db already has {len(seis_models_db)} "
          "seismicity models configured"
          f" and {len(haz_models_db)} hazard models configured")
    seis_model_names = [m.name for m in seis_models_db]
    haz_model_names = [m.name for m in haz_models_db]
    # create models
    models = create_models()
    for m in models:
        if m.name in seis_model_names or m.name in haz_model_names:
            pass
        else:
            store.add(m)
    seis_models_db = store.session.query(SeismicityModel).all()
    haz_models_db = store.session.query(HazardModel).all()
    print(f"The db now has {len(seis_models_db)} seismicity models configured"
          f" and {len(haz_models_db)} hazard models configured")

    create_bedretto_25_nov_project(store)
    print("created project")
    store.save()
    store.close()
