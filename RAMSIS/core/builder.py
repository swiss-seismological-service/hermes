# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Object creation and building facilities.
"""
import datetime
import functools

from ramsis.datamodel.forecast import (
    Forecast, ForecastScenario, ForecastStage, EStage)
from ramsis.datamodel.seismicity import SeismicityModelRun
from ramsis.datamodel.model import EModel


# NOTE(damb): The approach chosen is similar to matplotlib's pyplot builder
# interface. A detailed explanation is provided at:
# https://python-patterns.guide/gang-of-four/builder/
# -----------------------------------------------------------------------------

def seismicity_stage(store, models=[], **kwargs):
    """
    Build a seismicity forecast stage.

    :param store: Reference to RAMSIS store
    :type store: :py:class:`RAMSIS.core.store.Store`
    """
    # TODO(damb): Add models enabled
    return ForecastStage.create(
        EStage.SEISMICITY,
        runs=[SeismicityModelRun(model=m)
              for m in store._load_models(model_type=EModel.SEISMICITY)
              if m.enabled])


def seismicity_skill_stage(store):
    """
    Build a seismicity skill forecast stage.

    :param store: Reference to RAMSIS store
    :type store: :py:class:`RAMSIS.core.store.Store`
    """

    return ForecastStage.create(EStage.SEISMICITY_SKILL)


def hazard_stage(store):
    """
    Build a hazard forecast stage.

    :param store: Reference to RAMSIS store
    :type store: :py:class:`RAMSIS.core.store.Store`
    """
    return ForecastStage.create(EStage.HAZARD)


def risk_stage(store):
    """
    Build a risk forecast stage.

    :param store: Reference to RAMSIS store
    :type store: :py:class:`RAMSIS.core.store.Store`
    """
    return ForecastStage.create(EStage.RISK)


def default_scenario(store, future_wells=[], config=None, name=None, **kwargs):
    """
    Build a *default* forecast scenario.

    :param store: Reference to RAMSIS store
    :type store: :py:class:`RAMSIS.core.store.Store`
    :param future_wells: List of *future* planned wells (with an
    :py:class:`ramsis.datamodel.hydraulics.InjectionPlan` attached).
    :type future_wells: list of :py:class:`ramsis.datamodel.well.InjectionWell`
    :param dict config: scenario configuration dictionary
    :param name: Forecast scenario name
    :type name: str or None
    """
    DEFAULT_SCENARIO_CONFIG = {
        'stages': [
            {'seismicity': {
                'enabled': True,
                'models': [], }},
            {'seismicity_skill': {
                'enabled': False, }},
            {'hazard': {
                'enabled': True, }},
            {'risk': {
                'enabled': True, }}
        ]
    }

    if not config:
        config = DEFAULT_SCENARIO_CONFIG

    stages = []
    if 'seismicity' in config and config['seismicity'].get('enabled', True):
        stages.append(seismicity_stage(store),
                      models=config['seismicity'].get('models', []))
    if ('seismicity_skill' in config and
            config['seismicity_skill'].get('enabled', False)):
        stages.append(seismicity_skill_stage(store))
    if 'hazard' in config and config['hazard'].get('enabled', True):
        stages.append(hazard_stage(store))
    if 'risk' in config and config['risk'].get('enabled', True):
        stages.append(risk_stage(store))

    return ForecastScenario(
        config=config,
        name='Scenario' if name is None else name,
        stages=stages,
        wells=future_wells)


def default_forecast(store, starttime, endtime, num_scenarios=1, name=None):
    """
    Build a *default* forecast.

    :param store: Reference to RAMSIS store
    :type store: :py:class:`RAMSIS.core.store.Store`
    :param starttime: Starttime of the forecast
    :type starttime: :py:class:`datetime.datetime`
    :param endtime: Endtime of the forecast
    :type endtime: :py:class:`datetime.datetime`
    :param int num_scenarios: Number of default scenarios attached.
    :param name: Name of the forecast
    :type name: str or None
    """
    return Forecast(name='Forecast' if name is None else name,
                    starttime=starttime, endtime=endtime,
                    creationinfo_creationtime=datetime.datetime.utcnow(),
                    scenarios=[default_scenario(store)
                               for s in range(num_scenarios)])


empty_forecast = functools.partial(default_forecast, None, num_scenarios=0)
