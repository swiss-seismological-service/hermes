# -*- encoding: utf-8 -*-
"""
Manages the history of induced seismicity forecasts (inluding planned future
forecasts) and related classes.


Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from math import log, factorial

from sqlalchemy import Column, Integer, Float, DateTime, String, \
    ForeignKey, PickleType
from sqlalchemy.orm import relationship, reconstructor
from sqlalchemy.orm.collections import attribute_mapped_collection
from ormbase import OrmBase
from signal import Signal
from skilltest import SkillTest
from calculationstatus import CalculationStatus


class ForecastSet(OrmBase):
    """
    Parent object for forecasts

    """
    # region ORM Declarations
    __tablename__ = 'forecast_sets'
    id = Column(Integer, primary_key=True)
    # Project relation
    project_id = Column(Integer, ForeignKey('projects.id'))
    project = relationship('Project', back_populates='forecast_set')
    # Forecast relation
    forecasts = relationship('Forecast', back_populates='forecast_set',
                             cascade='all, delete-orphan',
                             order_by='Forecast.forecast_time')
    # endregion

    def __init__(self):
        self.forecasts_changed = Signal()

    @reconstructor
    def init_on_load(self):
        self.forecasts_changed = Signal()

    def add_forecast(self, forecast):
        """ Appends a new forecast and fires the changed signal """
        self.forecasts.append(forecast)
        self.forecasts_changed.emit()

    def forecast_at(self, t):
        """ Return the forecast scheduled for t """
        try:
            return next(f for f in self.forecasts if f.forecast_time == t)
        except StopIteration:
            return None


class Forecast(OrmBase):
    """ Planned or completed forecast """
    # region ORM Declarations
    __tablename__ = 'forecasts'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    forecast_time = Column(DateTime)
    forecast_interval = Column(Float)
    mc = Column(Float)
    m_min = Column(Integer)
    m_max = Column(Integer)
    # ForecastSet relation
    forecast_set_id = Column(Integer, ForeignKey('forecast_sets.id'))
    forecast_set = relationship('ForecastSet', back_populates='forecasts')
    # ForecastInput relation
    input = relationship('ForecastInput', back_populates='forecast',
                         cascade='all, delete-orphan', uselist=False)
    # ForecastResult relation
    results = relationship('ForecastResult', back_populates='forecast',
                           cascade='all, delete-orphan')
    # endregion

    @property
    def complete(self):
        # FIXME: also check all stages are complete
        if len(self.input.scenarios) == len(self.results):
            return True
        else:
            return False

    @property
    def project(self):
        """ Shortcut to the project """
        return self.forecast_set.project

    def add_scenario(self, scenario):
        """ Appends a new scenario and fires the changed signal """
        self.input.scenarios.append(scenario)
        self.input.forecast.forecast_set.forecasts_changed.emit()

    def remove_scenario(self, scenario):
        """ Removes a scenario and fires the changed signal """
        try:
            self.input.scenarios.remove(scenario)
            self.input.forecast.forecast_set.forecasts_changed.emit()
        except ValueError as e:
            raise e


class ForecastInput(OrmBase):

    # region ORM Declarations
    __tablename__ = 'forecast_inputs'
    id = Column(Integer, primary_key=True)
    # Forecast relation
    forecast_id = Column(Integer, ForeignKey('forecasts.id'))
    forecast = relationship('Forecast', back_populates='input')
    # SnapshotCatalog relation
    # We handle delete-orphan manually for seismic catalogs
    input_catalog = relationship('SeismicCatalog',
                                 uselist=False,
                                 back_populates='forecast_input',
                                 cascade='all')
    # Scenario relation
    scenarios = relationship('Scenario', back_populates='forecast_input',
                             cascade='all, delete-orphan')
    # endregion


class ForecastResult(OrmBase):
    """
    Results of one forecast run

    `ForecastResult` holds the results of all `Stages <Stage>` from the
    execution of a `ForecastJob`.

    """

    # region ORM declarations
    __tablename__ = 'forecast_results'
    id = Column(Integer, primary_key=True)
    # hazard stage
    hazard_result = relationship('HazardResult', uselist=False,
                                 back_populates='forecast_result',
                                 cascade='all, delete-orphan')
    # risk stage
    risk_result = relationship('RiskResult', back_populates='forecast_result',
                               cascade='all, delete-orphan', uselist=False)
    # Forecast relation
    forecast_id = Column(Integer, ForeignKey('forecasts.id'))
    forecast = relationship('Forecast', back_populates='results')
    # ISModelResult relation
    model_results = relationship('ModelResult', cascade='all, delete-orphan',
                                 back_populates='forecast_result',
                                 collection_class=attribute_mapped_collection(
                                     'model_id'))
    # Scenario relation
    scenario = relationship('Scenario', back_populates='forecast_result',
                            uselist=False)
    # endregion

    def __init__(self):
        self.result_changed = Signal()

    @reconstructor
    def init_on_load(self):
        self.result_changed = Signal()


class HazardResult(OrmBase):
    # region ORM declarations
    __tablename__ = 'hazard_results'
    id = Column(Integer, primary_key=True)
    # relationships
    forecast_result_id = Column(Integer, ForeignKey('forecast_results.id'))
    forecast_result = relationship('ForecastResult',
                                   back_populates='hazard_result')
    status = relationship('CalculationStatus', back_populates='hazard_result',
                          cascade='all', uselist=False)
    # endregion


class RiskResult(OrmBase):
    # region ORM declarations
    __tablename__ = 'risk_results'
    id = Column(Integer, primary_key=True)
    # relationships
    forecast_result_id = Column(Integer, ForeignKey('forecast_results.id'))
    forecast_result = relationship('ForecastResult',
                                   back_populates='risk_result')
    status = relationship('CalculationStatus', back_populates='risk_result',
                          cascade='all', uselist=False)
    # endregion


class Scenario(OrmBase):
    """
    Each forecast scenario has a specific planned injection scenario and
    model / stages configuration.
    
    The *config* dict holds the configuration for each scenario instance:
    {
        run_is_forecast: True / False
        run_hazard: True / False
        run_risk: True / False
        disabled_models: [model_id, ...]
    }
    
    Scenario emits the *scenario_changed* signal if its configuration or
    injection plan changes. In the former case, the signal carries the *config*
    dict.
    
    """

    def __init__(self):
        super(Scenario, self).__init__()
        self.config = {
            'run_is_forecast': True,
            'run_hazard': True,
            'run_risk': True,
            'disabled_models': []
        }
        self.scenario_changed = Signal()

    # region ORM declarations
    __tablename__ = 'scenarios'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    # Configuration as python dict
    config = Column(PickleType)
    # ForecastInput relation
    forecast_input_id = Column(Integer, ForeignKey('forecast_inputs.id'))
    forecast_input = relationship('ForecastInput', back_populates='scenarios')
    # InjectionPlan relation
    injection_plan = relationship('InjectionPlan',
                                  cascade='all, delete-orphan',
                                  back_populates='scenario',
                                  uselist=False)
    # ForecastResult relation
    forecast_result_id = Column(Integer, ForeignKey('forecast_results.id'))
    forecast_result = relationship('ForecastResult',
                                   back_populates='scenario')
    # endregion

    @property
    def project(self):
        """ Shortcut to the project """
        return self.forecast_input.forecast.project

    @reconstructor
    def init_on_load(self):
        self.scenario_changed = Signal()


def log_likelihood(forecast, observation):
    """
    Computes the log likelihood of an observed rate given a forecast

    The forecast value is interpreted as expected value of a poisson
    distribution. The function expects scalars or numpy arrays as input. In the
    latter case it computes the LL for each element.

    :param float forecast: forecasted rate
    :param float observation: observed rate
    :return: log likelihood for each element of the input

    """
    ll = -forecast + observation * log(forecast) - log(factorial(observation))
    return ll


class ModelResult(OrmBase):
    """
    Result from a single forecast `Model`. The result either contains actual
    result values in `cum_result` and optionally `vol_results` or a reason
    why no result is available in `failure_reason`. The `failed` attribute
    indicates whether results are available or not.

    For models that compute a single value for the entire volume, the
    `rate_prediction` attribute will contain that value. Some models, such as
    `Shapiro`, have more fine grained spatial resolution. Those store the
    cumulative forecast in `rate_prediction` and the results for individual 
    voxels are linked from there.

    :ivar model_id: The id of the model that created the forecast
    :ivar CalculationStatus status: The status of the calculation
    :ivar RatePrediction rate_prediction: Forecast result (cumulative). May
        be linked to further volumetric sub-results
    :ivar SkillTest skill_test: Model prediction skill test. Available once the
        result has been evaluated against measured rates.

    """

    # region ORM declarations
    __tablename__ = 'model_results'
    id = Column(Integer, primary_key=True)
    model_id = Column(String)
    status = relationship('CalculationStatus', uselist=False,
                          back_populates='model_result',
                          cascade='all')
    # ForecastResult relation
    forecast_result_id = Column(Integer, ForeignKey('forecast_results.id'))
    forecast_result = relationship('ForecastResult',
                                   back_populates='model_results')
    # SkillTest relation
    skill_test_id = Column(Integer, ForeignKey('skill_tests.id'))
    skill_test = relationship(SkillTest, back_populates='model_result')
    # ISPrediction relation
    rate_prediction = relationship('RatePrediction',
                                   uselist=False,
                                   back_populates='model_result',
                                   cascade='all, delete-orphan')
    # endregion

    def __init__(self, model_id):
        self.model_id = model_id

    @property
    def reviewed(self):
        """
        True if the forecast result has been evaluated against real measured
        seismicity rates through `review`.

        """
        return self._reviewed

    def compute_cumulative(self):
        """
        Computes the cumulative result from the individual spatial results.

        """
        rate = sum(r.rate for r in self.vol_results)
        # FIXME: averaging the b_val is most likely completely wrong
        b_val = sum(r.b_val for r in self.vol_results) / len(self.vol_results)
        prob = sum(r.prob for r in self.vol_results)
        self.cum_result = RatePrediction(rate, b_val, prob)

    def review(self, observations):
        """
        Reviews results based on the 'truth' data in event **observations** for
        the forecast period and assigns a score to the model.

        :param observations: the observed events for the forecast period
        :type observations: list of SeismicEvent objects

        """
        # FIXME: move this to the skill_test
        pass
        # logger = logging.getLogger(__name__)
        # logger.setLevel(logging.DEBUG)
        # if self.vol_results:
        #     # TODO: compute LL per voxel
        #     # at the moment we don't know the region for each volumetric
        #     # result.
        #     # for result in self.vol_results:
        #     #     region = result.region
        #     #     obs = len([e for e in observations if e.in_region(region)])
        #     #     result.score = log_likelihood(result.review, obs)
        #     pass
        # self.cum_result.score = log_likelihood(self.cum_result.rate,
        #                                        len(observations))
        # self._reviewed = True
        # logger.debug('{} at {}: LL = {}'.format(self.model.title,
        #                                         self.t_run,
        #                                         self.result.score.LL))

    def get_rates(self):
        rates = self._get_rates(self.rate_prediction)
        return None if not rates else rates

    def _get_rates(self, rates):
        if rates is not None:
            r = rates.vol_predictions
            return [r] + self._get_rates(r)
        return []


class RatePrediction(OrmBase):
    """
    Result container for a single forecasted seismic rate

    :ivar float rate: Forecasted seismicity rate
    :ivar float b_val: Expected b value
    :ivar float prob: Expected probability of exceedance
    :ivar score: Score (log-likelihood value) of the forecast after review
    :ivar model_result: Reference to the model result that this result belongs
        to.

    """

    # region ORM declarations
    __tablename__ = 'rate_predictions'
    id = Column(Integer, primary_key=True)
    rate = Column(Float)
    b_val = Column(Float)
    prob = Column(Float)
    score = Column(Float)
    # ModelResult relation
    model_result_id = Column(Integer, ForeignKey('model_results.id'))
    model_result = relationship('ModelResult',
                                back_populates='rate_prediction')
    # Configures the one-to-many relationship between RatePrediction's
    # vol_predictions and this entity (self referential)
    parent_id = Column(Integer, ForeignKey('rate_predictions.id'))
    vol_predictions = relationship('RatePrediction',
                                   cascade="all, delete-orphan")
    # endregion

    def __init__(self, rate, b_val, prob):
        self.prob = prob
        self.rate = rate
        self.b_val = b_val
        self.score = None
        self.model_result = None
