"""
Bootstrap the Bedretto 2020 Jan/Feb data projects
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
from ramsis.datamodel.model import EModel # noqa

from RAMSIS.core.builder import (
    default_project, default_forecast, default_scenario)
from RAMSIS.core.store import Store
from RAMSIS.io.hydraulics import HYDWSBoreholeHydraulicsDeserializer
from RAMSIS.io.seismics import QuakeMLCatalogDeserializer

DIRPATH = os.path.dirname(os.path.abspath(__file__))
DIR_HYDRAULICS = "hyd"

DIR_SEISMICS = "seismics"
PATH_SEISMICS = 'Bedretto_test_seismic_catalog.xml'
PATH_HYDRAULICS_1 = \
    "ben_dyer_cb1_minute_sampled_20200205110837_20200206104800_193.22m.json"

PROJECT_STARTTIME_1 = datetime(2020, 2, 5, 11, 0)
PROJECT_ENDTIME_1 = datetime(2020, 2, 6, 11, 0)

FORECAST_STARTTIME_1 = datetime(2020, 2, 5, 19, 0)
FORECAST_ENDTIME_1 = datetime(2020, 2, 6, 10, 48)

PATH_HYDRAULICS_2 = \
    "ben_dyer_cb1_minute_sampled_20200206115312_20200207101100_176.78m.json"

PROJECT_STARTTIME_2 = datetime(2020, 2, 6, 11, 50)
PROJECT_ENDTIME_2 = datetime(2020, 2, 7, 10, 11)

FORECAST_STARTTIME_2 = datetime(2020, 2, 6, 19, 0)
FORECAST_ENDTIME_2 = datetime(2020, 2, 7, 10, 11)

# NOTE(sarsonl): Reservoir definition containing all seismic events.
#RESERVOIR = {"x": [-200, -180, -160, -140, -120, -100, -80, -60, -40, -20, 0],
#             "y": [-200, -180, -160, -140, -120, -100, -80, -60, -40, -20, 0],
#             "z": [1200, 1220, 1240, 1260, 1280, 1300, 1320, 1340,
#                   1360, 1380, 1400]}

RESERVOIR = {
    "x": [-300., -290., -280., -270., -260., -250., -240., -230., -220.,
       -210., -200., -190., -180., -170., -160., -150., -140., -130.,
       -120., -110., -100.,  -90.,  -80.,  -70.,  -60.,  -50.,  -40.,
        -30.,  -20.,  -10.,    0.,   10.,   20.,   30.,   40.,   50.,
         60.,   70.,   80.,   90.,  100.,  110.,  120.,  130.,  140.,
        150.,  160.,  170.,  180.,  190.,  200.,  210.,  220.,  230.,
        240.,  250.,  260.,  270.,  280.,  290.,  300.,  310.,  320.,
        330.],
    "y": [-300., -290., -280., -270., -260., -250., -240., -230., -220.,
       -210., -200., -190., -180., -170., -160., -150., -140., -130.,
       -120., -110., -100.,  -90.,  -80.,  -70.,  -60.,  -50.,  -40.,
        -30.,  -20.,  -10.,    0.,   10.,   20.,   30.,   40.,   50.,
         60.,   70.,   80.,   90.,  100.,  110.,  120.,  130.,  140.,
        150.,  160.,  170.,  180.,  190.,  200.,  210.,  220.,  230.,
        240.,  250.,  260.,  270.,  280.,  290.,  300.,  310.,  320.,
        330.],
    "z": [1069., 1079., 1089., 1099., 1109., 1119., 1129., 1139., 1149.,
       1159., 1169., 1179., 1189., 1199., 1209., 1219., 1229., 1239.,
       1249., 1259., 1269., 1279., 1289., 1299., 1309., 1319., 1329.,
       1339., 1349., 1359., 1369., 1379., 1389., 1399., 1409., 1419.,
       1429., 1439., 1449., 1459., 1469., 1479., 1489., 1499., 1509.,
       1519., 1529., 1539., 1549., 1559., 1569., 1579., 1589., 1599.,
       1609., 1619., 1629., 1639., 1649., 1659., 1669., 1679., 1689.,
       1699.]}
RAMSIS_PROJ = ("+proj=somerc +lat_0=46.95240555555556 "
               "+lon_0=7.439583333333333 +k_0=1 +x_0=2600000 "
               "+y_0=1200000 +ellps=bessel "
               "+towgs84=674.374,15.056,405.346,0,0,0,0 "
               "+units=m +no_defs")

WGS84_PROJ = "epsg:4326"
REFERENCE_X = 2679720.70
REFERENCE_Y = 1151600.13


def create_models():
    path_templates = "/home/sarsonl/repos/em1/rt-ramsis/oq_templates_bootstrap"
    URL_EM1 = 'http://ramsis-em1'
    URL_HM1 = 'http://ramsiswin:5007'
    EM1_SFMWID = 'EM1'
    HM1_SFMWID = 'HM1'
    HOUR_IN_SECS = 3600
    DAY_IN_SECS = 86400
    HIGH_EVENT_THRESH = 100
    LOW_EVENT_THRESH = 10
    SEISMICITY_MODEL_TEMPLATE = \
        f"{path_templates}/single_reservoir_seismicity_template.xml"

    # NOTE(sarsonl): "em1_training_epoch_duration" is optional and defaults to
    # None in the model if not provided. This means the model trains for the
    # maximum length of time possible from data provided, which is the time
    # between first and last hydraulic sample with with positive topflow.

    base_config = {"em1_training_events_threshold": LOW_EVENT_THRESH,
                   "em1_training_magnitude_bin": 0.1,
                   "em1_threshold_magnitude": 0}

    retval = []

    m = SeismicityModel(
        name='EM1-Full-Training-Low-Event-Threshold',
        config=base_config,
        sfmwid=EM1_SFMWID,
        enabled=True,
        url=URL_EM1,
        seismicitymodeltemplate=SEISMICITY_MODEL_TEMPLATE)
    retval.append(m)

    m = SeismicityModel(
        name='EM1-Hour-Moving-Window-Low-Event-Threshold',
        config={**base_config,
                **{"em1_training_epoch_duration": HOUR_IN_SECS}},
        sfmwid=EM1_SFMWID,
        enabled=False,
        url=URL_EM1,
        seismicitymodeltemplate=SEISMICITY_MODEL_TEMPLATE)
    retval.append(m)

    m = SeismicityModel(
        name='EM1-Day-Moving-Window-Low-Event-Threshold',
        config={**base_config,
                **{"em1_training_epoch_duration": DAY_IN_SECS}},
        sfmwid=EM1_SFMWID,
        enabled=True,
        url=URL_EM1,
        seismicitymodeltemplate=SEISMICITY_MODEL_TEMPLATE)
    retval.append(m)

    m = SeismicityModel(
        name='EM1-Full-Training-High-Event-Threshold',
        config={**base_config,
                **{"em1_training_events_threshold": HIGH_EVENT_THRESH}},
        sfmwid=EM1_SFMWID,
        enabled=False,
        url=URL_EM1,
        seismicitymodeltemplate=SEISMICITY_MODEL_TEMPLATE)
    retval.append(m)

    m = SeismicityModel(
        name='EM1-Hour-Moving-Window-High-Event-Threshold',
        config={**base_config,
                **{"em1_training_epoch_duration": HOUR_IN_SECS,
                   "em1_training_events_threshold": HIGH_EVENT_THRESH}},
        sfmwid=EM1_SFMWID,
        enabled=False,
        url=URL_EM1,
        seismicitymodeltemplate=SEISMICITY_MODEL_TEMPLATE)
    retval.append(m)

    m = SeismicityModel(
        name='EM1-Day-Moving-Window-High-Event-Threshold',
        config={**base_config,
                **{"em1_training_epoch_duration": DAY_IN_SECS,
                   "em1_training_events_threshold": HIGH_EVENT_THRESH}},
        sfmwid=EM1_SFMWID,
        enabled=False,
        url=URL_EM1,
        seismicitymodeltemplate=SEISMICITY_MODEL_TEMPLATE)
    retval.append(m)

    m = SeismicityModel(
        name='HM1-default-config',
        config={"hm1_test_mode": False,
                "hm1_training_epoch_duration": 3600,
                "hm1_training_magnitude_bin": 0.1,
                "hm1_training_events_threshold": 5,
                "hm1_max_iterations": -1
                },
        sfmwid=HM1_SFMWID,
        enabled=False,
        url=URL_HM1,
        seismicitymodeltemplate=SEISMICITY_MODEL_TEMPLATE)
    retval.append(m)

    m = SeismicityModel(
        name='HM1-full_bedretto_config',
        config={"hm1_test_mode": False,
                "hm1_training_epoch_duration": 180,
                "hm1_training_magnitude_bin": 0.01,
                "hm1_training_events_threshold": 4,
                "hm1_max_iterations": -1,
                "hm1_seed_settings":  {
            "slope_sigma1": 0.0,
            "slope_sigma3": 0.0,
            "sigma1_std": 20, #optimized
            "sigma3_std": 0,
            "fluid_density": 985,
            "gravity": 0,
            "inter_sigma1": 22.5,
            "inter_sigma3": 10,
            "b_vs_depth_range": True,
            "min_failure_pressure": 15, #optimized
            "stressdrop_coeff": 1., #optimized
            "cohesion_mean": 0,
            "friction_mean": 0.6,
            "PoissonDensity": 1.e-6}, # optimized
        "hm1_external_solution_settings": {
            # CAPS: Order of columns for numpy array pressure, time, coordinates (1 in 1D)
            "FileCols": [2, 0, 1],
            # CAPS: Coefficients of pressure, time, coordinates
            "FileConvs": [1.e-6, 24.*3600., 1.],
            # CAPS: Number of lines to skip when reading Tecplot files
            "SkipLines": 6,
            # HM1 properties
            "fraction_seismic_cloud": 2.5, #extent of stimulation area
            "borehole_storage_coefficient": 0.002,
            "borehole_transmissivity": 1000,
            "initial_storage_coeff": 0.002,
            "initial_transmissivity": 5.E-07,
            # Input to Dieter's HM1 code as a parameter
            # The smaller the time step, the more rapidly the adaption of the
            # calibration parameters.
            "deltat": 10,
            # HM1 mesh geometry
            "mesh_extent": 300,
            "alfa_rate_of_growth": 2,
            "size_first_element": 0.02},
        "hm1_caps_kd_settings": {
            "RefinementRatio": 2,
            "EnableScrOutput": False}},
        #config={"hm1_test_mode": False,
        #        "hm1_training_epoch_duration": 3600,
        #        "hm1_training_magnitude_bin": 0.1,
        #        "hm1_training_events_threshold": 5,
        #        "hm1_max_iterations": -1,
        #        "hm1_seed_settings": {
        #            "slope_sigma1": 0.0,
        #            "slope_sigma3": 0.0,
        #            "sigma3_std": 10.0,
        #            "fluid_density": 985.0,
        #            "gravity": 0.0,
        #            "inter_sigma1": 16.5,
        #            "inter_sigma3": 4.0,
        #            "friction_mean": 0.6,
        #            "cohesion_mean": 0.0,
        #            "stressdrop_coeff": 3.0,
        #            "PoissonDensity": 1.0e-6,
        #            "sigma1_std": 10.0,
        #            "min_failure_pressure": 15.0},
        #        "hm1_external_solution_settings": {
        #            "deltat": 6}
        #        },
        sfmwid=HM1_SFMWID,
        enabled=True,
        url=URL_HM1,
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


def create_bedretto_5_6_feb_project(store):
    # FIXME(damb): TheV project and deserializers are configured without any
    # srid. As a consequence, no transformation is performed when importing
    # data.

    # import seismic catalog
    deserializer = QuakeMLCatalogDeserializer(
        ramsis_proj=RAMSIS_PROJ,
        external_proj=WGS84_PROJ,
        ref_easting=REFERENCE_X,
        ref_northing=REFERENCE_Y,
        transform_func_name='pyproj_transform_to_local_coords')

    with open(join(DIRPATH, DIR_SEISMICS, PATH_SEISMICS), 'rb') as ifd:
        cat = deserializer.load(ifd)

    # create project
    project_1 = default_project(
        name='Bedretto 2020 5th-6th Feb',
        description='Bedretto project 5th-6th Feb',
        starttime=PROJECT_STARTTIME_1,
        endtime=PROJECT_ENDTIME_1,
        spatialreference=RAMSIS_PROJ,
        referencepoint_x=REFERENCE_X,
        referencepoint_y=REFERENCE_Y)

    # import the rest of hydraulics
    deserializer = HYDWSBoreholeHydraulicsDeserializer(
        ramsis_proj=RAMSIS_PROJ,
        external_proj=WGS84_PROJ,
        ref_easting=REFERENCE_X,
        ref_northing=REFERENCE_Y,
        transform_func_name='pyproj_transform_to_local_coords')

    print("reading: ", PATH_HYDRAULICS_1)
    with open(join(DIRPATH, DIR_HYDRAULICS, PATH_HYDRAULICS_1), 'rb') as ifd:
        well_1 = deserializer.load(ifd)
    project_1.seismiccatalog = cat
    project_1.well = well_1
    store.add(project_1)

    store.save()

    # create forecast
    fc_1 = default_forecast(store, starttime=FORECAST_STARTTIME_1,
                            endtime=FORECAST_ENDTIME_1,
                            num_scenarios=0,
                            name='Bedretto Forecast default')

    # add exemplary scenario
    fc_1.project = project_1
    scenario_1 = default_scenario(store, name='Bedretto Scenario 1, 1hr')
    fc_1.scenarios = [scenario_1]
    seismicity_stage = scenario_1[EStage.SEISMICITY]
    seismicity_stage.config = {'prediction_bin_duration': 3600}
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
    with open(join(DIRPATH, DIR_HYDRAULICS, PATH_HYDRAULICS_1), 'rb') as ifd:
        scenario_1.well = deserializer.load(ifd)
    store.add(fc_1)
    store.add(scenario_1)


def create_bedretto_6_7_feb_project(store):
    # FIXME(damb): TheV project and deserializers are configured without any
    # srid. As a consequence, no transformation is performed when importing
    # data.

    # import seismic catalog
    deserializer = QuakeMLCatalogDeserializer(
        ramsis_proj=RAMSIS_PROJ,
        external_proj=WGS84_PROJ,
        ref_easting=REFERENCE_X,
        ref_northing=REFERENCE_Y,
        transform_func_name='pyproj_transform_to_local_coords')

    with open(join(DIRPATH, DIR_SEISMICS, PATH_SEISMICS), 'rb') as ifd:
        cat2 = deserializer.load(ifd)

    # create project
    project_2 = default_project(
        name='Bedretto 2020 6th-7th Feb',
        description='Bedretto project 6th-7th Feb',
        starttime=PROJECT_STARTTIME_2,
        endtime=PROJECT_ENDTIME_2,
        spatialreference=RAMSIS_PROJ,
        referencepoint_x=REFERENCE_X,
        referencepoint_y=REFERENCE_Y)

    # import the rest of hydraulics
    deserializer = HYDWSBoreholeHydraulicsDeserializer(
        ramsis_proj=RAMSIS_PROJ,
        external_proj=WGS84_PROJ,
        ref_easting=REFERENCE_X,
        ref_northing=REFERENCE_Y,
        transform_func_name='pyproj_transform_to_local_coords')

    print("reading: ", PATH_HYDRAULICS_2)
    with open(join(DIRPATH, DIR_HYDRAULICS, PATH_HYDRAULICS_2), 'rb') as ifd:
        well_2 = deserializer.load(ifd)
    project_2.seismiccatalog = cat2
    project_2.well = well_2
    store.add(project_2)
    store.save()

    # create second forecast
    fc_2 = default_forecast(store, starttime=FORECAST_STARTTIME_2,
                            endtime=FORECAST_ENDTIME_2,
                            num_scenarios=0,
                            name='Bedretto Forecast default')

    # add exemplary scenario
    fc_2.project = project_2
    scenario_2 = default_scenario(store, name='Bedretto Scenario 1, 1hr')
    fc_2.scenarios = [scenario_2]
    seismicity_stage = scenario_2[EStage.SEISMICITY]
    seismicity_stage.config = {'prediction_bin_duration': 3600}
    scenario_2.reservoirgeom = RESERVOIR
    deserializer = HYDWSBoreholeHydraulicsDeserializer(
        ramsis_proj=RAMSIS_PROJ,
        external_proj=WGS84_PROJ,
        ref_easting=REFERENCE_X,
        ref_northing=REFERENCE_Y,
        transform_func_name='pyproj_transform_to_local_coords',
        plan=True)

    hazard_stage = scenario_2[EStage.HAZARD]
    hazard_models = store.load_models(model_type=EModel.HAZARD)
    hazard_stage.model = hazard_models[0]
    with open(join(DIRPATH, DIR_HYDRAULICS, PATH_HYDRAULICS_2), 'rb') as ifd:
        scenario_2.well = deserializer.load(ifd)
    store.add(fc_2)
    store.add(scenario_2)


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
    assert 'Bedretto 2020 6th-7th Feb' not in project_names, \
        "Project name already exists"
    assert 'Bedretto 2020 5th-6th Feb' not in project_names, \
        "Project name already exists"

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

    create_bedretto_5_6_feb_project(store)
    print("created project for bedretto data 5-6th feb")
    create_bedretto_6_7_feb_project(store)
    print("created project for bedretto data 6-7th feb")
    store.save()
    store.close()
