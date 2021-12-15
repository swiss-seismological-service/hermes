"""
Create new project for November stimulations, borehole: CB1
"""
import os
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
from ramsis.datamodel.seismics import SeismicObservationCatalog, SeismicEvent  # noqa
from ramsis.datamodel.settings import ProjectSettings  # noqa
from ramsis.datamodel.status import Status  # noqa
from ramsis.datamodel.well import InjectionWell, WellSection  # noqa
from ramsis.datamodel.model import EModel  # noqa

from RAMSIS.core.builder import (
    default_project, default_forecast, default_scenario)
from RAMSIS.core.store import Store

DIRPATH = os.path.dirname(os.path.abspath(__file__))

PROJECT_STARTTIME_1 = datetime(2020, 11, 5, 0, 0)

FORECAST_STARTTIME_1 = datetime(2020, 11, 5, 12, 0)
# making up the forecast times as we are not sure when stimulation will begin.
FORECAST_ENDTIME_1 = datetime(2020, 11, 5, 15, 0)

# NOTE(sarsonl): Reservoir definition containing all seismic events.
# autopep8: off
RESERVOIR = {
    "x": [-300., -290., -280., -270., -260., -250., -240., -230., -220., # noqa
          -210., -200., -190., -180., -170., -160., -150., -140., -130., # noqa
          -120., -110., -100.,  -90.,  -80.,  -70.,  -60.,  -50.,  -40., # noqa
           -30.,  -20.,  -10.,    0.,   10.,   20.,   30.,   40.,   50., # noqa
            60.,   70.,   80.,   90.,  100.,  110.,  120.,  130.,  140., # noqa
           150.,  160.,  170.,  180.,  190.,  200.,  210.,  220.,  230., # noqa
           240.,  250.,  260.,  270.,  280.,  290.,  300.,  310.,  320., # noqa
           330.], # noqa
    "y": [-300., -290., -280., -270., -260., -250., -240., -230., -220., # noqa
          -210., -200., -190., -180., -170., -160., -150., -140., -130., # noqa
          -120., -110., -100.,  -90.,  -80.,  -70.,  -60.,  -50.,  -40., # noqa
           -30.,  -20.,  -10.,    0.,   10.,   20.,   30.,   40.,   50., # noqa
            60.,   70.,   80.,   90.,  100.,  110.,  120.,  130.,  140., # noqa
           150.,  160.,  170.,  180.,  190.,  200.,  210.,  220.,  230., # noqa
           240.,  250.,  260.,  270.,  280.,  290.,  300.,  310.,  320., # noqa
           330.], # noqa
    "z": [1069., 1079., 1089., 1099., 1109., 1119., 1129., 1139., 1149., # noqa
          1159., 1169., 1179., 1189., 1199., 1209., 1219., 1229., 1239., # noqa
          1249., 1259., 1269., 1279., 1289., 1299., 1309., 1319., 1329., # noqa
          1339., 1349., 1359., 1369., 1379., 1389., 1399., 1409., 1419., # noqa
          1429., 1439., 1449., 1459., 1469., 1479., 1489., 1499., 1509., # noqa
          1519., 1529., 1539., 1549., 1559., 1569., 1579., 1589., 1599., # noqa
          1609., 1619., 1629., 1639., 1649., 1659., 1669., 1679., 1689., # noqa
          1699.]} # noqa
# autopep8: on
RAMSIS_PROJ = ("+proj=somerc +lat_0=46.95240555555556 "
               "+lon_0=7.439583333333333 +k_0=1 +x_0=2600000 "
               "+y_0=1200000 +ellps=bessel "
               "+towgs84=674.374,15.056,405.346,0,0,0,0 "
               "+units=m +no_defs")

WGS84_PROJ = "epsg:4326"
REFERENCE_X = 2679720.70
REFERENCE_Y = 1151600.13

# the interval parameters are not used - todo remove
FDSNWS_URL = "http://bedretto-events.ethz.ch/fdsnws/event/1/query"
HYDWS_URL = "http://geo-ws03.ethz.ch:8080/hydws/v1/boreholes/c21pOmNoLmV0aHouc2VkL2JoL0NCMQ=="  # noqa


def create_models():
    path_templates = "/home/sarsonl/repos/em1/rt-ramsis/oq_templates_bootstrap"
    URL_EM1 = 'http://ramsis-em1:8080'
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
        enabled=True,
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
                "hm1_seed_settings": {
                    "slope_sigma1": 0.0,
                    "slope_sigma3": 0.0,
                    "sigma1_std": 20,  # optimized
                    "sigma3_std": 0,
                    "fluid_density": 985,
                    "gravity": 0,
                    "inter_sigma1": 22.5,
                    "inter_sigma3": 10,
                    "b_vs_depth_range": True,
                    "min_failure_pressure": 15,  # optimized
                    "stressdrop_coeff": 1.,  # optimized
                    "cohesion_mean": 0,
                    "friction_mean": 0.6,
                    "PoissonDensity": 1.e-6},  # optimized
                "hm1_external_solution_settings": {
                    # CAPS: Order of columns for numpy array pressure, time,
                    # coordinates (1 in 1D)
                    "FileCols": [2, 0, 1],
                    # CAPS: Coefficients of pressure, time, coordinates
                    "FileConvs": [1.e-6, 24. * 3600., 1.],
                    # CAPS: Number of lines to skip when reading Tecplot files
                    "SkipLines": 6,
                    # HM1 properties
                    # extent of stimulation area
                    "fraction_seismic_cloud": 2.5,
                    "borehole_storage_coefficient": 0.002,
                    "borehole_transmissivity": 1000,
                    "initial_storage_coeff": 0.002,
                    "initial_transmissivity": 5.E-07,
                    # Input to Dieter's HM1 code as a parameter
                    # The smaller the time step, the more rapidly the adaption
                    # of calibration parameters.
                    "deltat": 10,
                    # HM1 mesh geometry
                    "mesh_extent": 300,
                    "alfa_rate_of_growth": 2,
                    "size_first_element": 0.02},
                "hm1_caps_kd_settings": {
                    "RefinementRatio": 2,
                    "EnableScrOutput": False}},
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


def create_bedretto_nov_project(store, proj_name, proj_startdate,
                                proj_enddate, proj_description,
                                create_forecast,
                                forecast_startdate,
                                forecast_enddate):
    # FIXME(damb): TheV project and deserializers are configured without any
    # srid. As a consequence, no transformation is performed when importing
    # data.

    # create project
    project_1 = default_project(
        name=proj_name,
        description=proj_description,
        starttime=proj_startdate,
        endtime=proj_enddate,
        proj_string=RAMSIS_PROJ,
        referencepoint_x=REFERENCE_X,
        referencepoint_y=REFERENCE_Y)

    store.add(project_1)
    print("project settings: ", type(project_1.settings),
          dir(project_1.settings))
    project_1.settings['fdsnws_enable'] = True
    project_1.settings['hydws_enable'] = True
    project_1.settings['fdsnws_url'] = FDSNWS_URL
    project_1.settings['hydws_url'] = HYDWS_URL
    project_1.settings.commit()
    store.save()

    if create_forecast:
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
        # have not decided what bin duration should be,
        # so set an hour as default
        seismicity_stage.config = {'epoch_duration': 3600}
        scenario_1.reservoirgeom = RESERVOIR

        hazard_stage = scenario_1[EStage.HAZARD]
        hazard_models = store.load_models(model_type=EModel.HAZARD)
        hazard_stage.model = hazard_models[0]
        store.add(fc_1)
        store.add(scenario_1)


def valid_date(s):
    try:
        return datetime.strptime(s, "%d-%m-%YT%H:%M")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


def parse_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'db_url', type=str, metavar='URL',
        help=('DB URL indicating the database dialect and connection '
              'arguments.'))
    parser.add_argument("proj_startdate",
                        help="The project start datetime - "
                             "format DD-MM-YYYYTHH:MM",
                        type=valid_date)

    parser.add_argument('proj_name', type=str)
    parser.add_argument('create_forecast', type=bool)
    parser.add_argument(
        "--proj_enddate",
        help="The project end datetime - format DD-MM-YYYYTHH:MM",
        type=valid_date)
    parser.add_argument('--proj_description', type=str, default='')
    parser.add_argument(
        "--forecast_startdate",
        help="The forecast start datetime - format DD-MM-YYYYTHH:MM",
        type=valid_date)
    parser.add_argument(
        "--forecast_enddate",
        help="The forecast_endtime - format DD-MM-YYYYTHH:MM",
        type=valid_date)

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_cli()
    if args.create_forecast:
        assert (args.forecast_startdate and args.forecast_enddate)

    store = Store(args.db_url)
    success = store.init_db()
    if success:
        print("New db initialized")
    else:
        print("Error, db could not be initialized: ", success)
        raise Exception("DB could not be initialized")

    projects = store.session.query(Project).all()
    project_names = [p.name for p in projects]
    assert args.proj_name not in project_names, "Project name already exists"

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

    create_bedretto_nov_project(
        store, args.proj_name, args.proj_startdate,
        args.proj_enddate, args.proj_description, args.create_forecast,
        args.forecast_startdate, args.forecast_enddate)
    print("created project for Bedretto")
    store.save()
    store.close()
