# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Object creation and building facilities.
"""

import datetime
import functools

from ramsis.datamodel.forecast import (
    Forecast, ForecastScenario, ForecastStage, EStage)
from ramsis.datamodel.model import EModel
from ramsis.datamodel.project import Project
from ramsis.datamodel.seismicity import SeismicityModelRun
from ramsis.datamodel.status import Status


# NOTE(damb): The approach chosen is similar to matplotlib's pyplot builder
# interface. A detailed explanation is provided at:
# https://python-patterns.guide/gang-of-four/builder/
# -----------------------------------------------------------------------------

def seismicity_stage(**kwargs):
    """
    Build a seismicity forecast stage.
    """
    return ForecastStage.create(EStage.SEISMICITY, **kwargs)


def seismicity_skill_stage(**kwargs):
    """
    Build a seismicity skill forecast stage.
    """

    return ForecastStage.create(EStage.SEISMICITY_SKILL, **kwargs)


def hazard_stage(**kwargs):
    """
    Build a hazard forecast stage.
    """
    return ForecastStage.create(EStage.HAZARD, **kwargs)


def risk_stage(**kwargs):
    """
    Build a risk forecast stage.
    """
    return ForecastStage.create(EStage.RISK, **kwargs)


def default_scenario(store, name='Scenario', **kwargs):
    """
    Build a *default* forecast scenario.

    :param store: Reference to RAMSIS store
    :type store: :py:class:`RAMSIS.core.store.Store`
    :param name: Forecast scenario name
    :type name: str or None
    """

    DEFAULT_SCENARIO_CONFIG = {
        'stages': [
            {'seismicity': {
                'enabled': True,
                'config': {}, }},
            {'seismicity_skill': {
                'enabled': False,
                'config': {}, }},
            {'hazard': {
                'enabled': True,
                'config': {}, }},
            {'risk': {
                'enabled': True,
                'config': {}, }}
        ]
    }

    def create_stages(store, stage_config):
        """
        Create stages from a stage configuration.

        :param dict stage_config: Stage configuration

        :returns: list of stages
        :rtype: list of :py:class:`ramsis.datamodel.ForecastStage`
        """

        retval = []
        try:
            seismicity_stage_config = stage_config[0]['seismicity']
        except (IndexError, KeyError):
            pass
        else:
            enabled = seismicity_stage_config.get('enabled', True)
            if enabled:
                runs = [SeismicityModelRun(model=m, enabled=True,
                                           status=Status())
                        for m in store.load_models(
                            model_type=EModel.SEISMICITY)
                        if m.enabled]
                s = seismicity_stage(runs=runs, **seismicity_stage_config)
                retval.append(s)

        try:
            seismicity_skill_stage_config = stage_config[1]['seismicity_skill']
        except (IndexError, KeyError):
            pass
        else:
            enabled = seismicity_skill_stage_config.get('enabled', False)
            if enabled:
                retval.append(seismicity_skill_stage(enabled=enabled))

        try:
            hazard_stage_config = stage_config[2]['hazard']
        except (IndexError, KeyError):
            pass
        else:
            enabled = hazard_stage_config.get('enabled', True)
            if enabled:
                retval.append(hazard_stage(enabled=enabled))

        try:
            risk_stage_config = stage_config[3]['risk']
        except (IndexError, KeyError):
            pass
        else:
            enabled = risk_stage_config.get('enabled', True)
            if enabled:
                retval.append(risk_stage(enabled=enabled))

        return retval

    return ForecastScenario(
        name=name,
        config={},
        enabled=True,
        stages=create_stages(store, DEFAULT_SCENARIO_CONFIG['stages']))


def default_forecast(store, starttime, endtime, num_scenarios=1,
                     name='Forecast'):
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
    return Forecast(name=name, starttime=starttime, endtime=endtime,
                    creationinfo_creationtime=datetime.datetime.utcnow(),
                    enabled=True, config={},
                    scenarios=[default_scenario(store)
                               for s in range(num_scenarios)])


empty_forecast = functools.partial(default_forecast, None, num_scenarios=0)


def default_project(name='Project', description='',
                    starttime=datetime.datetime.utcnow(), endtime=None):
    """
    Build a *default* project.

    :param str name: The project's name
    :param str description: The project's description
    :param starttime: Starttime of the project
    :type starttime: :py:class:`datetime.datetime`
    :param endtime: Optional project endtime
    :type endtime: :py:class:`datetime.datetime`
    """
    return Project(name=name, description=description, starttime=starttime,
                   endtime=endtime, spatialreference='',
                   creationinfo_creationtime=datetime.datetime.utcnow())
