# -*- encoding: utf-8 -*-
"""
Manages the history of induced seismicity forecasts (inluding planned future
forecasts) and related classes.


Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from math import log, factorial

from sqlalchemy import Column, Integer, Float, DateTime, String, Boolean, \
    ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.inspection import inspect
from ormbase import OrmBase, DeclarativeQObjectMeta
from skilltest import SkillTest

from core.data.eventhistory import EventHistory

from PyQt4 import QtCore


class ForecastSet(EventHistory, OrmBase):
    """
    Planned and executed forecasts

    """
    __metaclass__ = DeclarativeQObjectMeta

    # region ORM Declarations
    __tablename__ = 'forecast_sets'
    id = Column(Integer, primary_key=True)
    # Project relation
    project_id = Column(Integer, ForeignKey('projects.id'))
    project = relationship('Project', back_populates='forecast_set')
    # Forecast relation
    forecasts = relationship('Forecast', back_populates='forecast_set',
                             cascade='all, delete-orphan')
    # endregion

    def __init__(self, store):
        super(ForecastSet, self).\
            __init__(store, Forecast,
                     date_time_attr=Forecast.forecast_time)


class Forecast(OrmBase):
    """
    Planned or executed forecast

    """
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
    input_id = Column(Integer, ForeignKey('forecast_inputs.id'))
    input = relationship('ForecastInput', back_populates='forecast')
    # ForecastResult relation
    result = relationship('ForecastResult', back_populates='forecast')
    # endregion


class ForecastInput(OrmBase):

    # region ORM Declarations
    __tablename__ = 'forecast_inputs'
    id = Column(Integer, primary_key=True)
    # Forecast relation
    forecast = relationship('Forecast', back_populates='input',
                            uselist=False)
    # SnapshotCatalog relation
    input_catalog = relationship('SeismicCatalog',
                                 uselist=False,
                                 back_populates='forecast_input',
                                 cascade='all, delete-orphan')
    # Scenario relation
    scenarios = relationship('Scenario', back_populates='forecast_inputs',
                             cascade='all, delete-orphan')
    # endregion


class ForecastResult(QtCore.QObject, OrmBase):
    """
    Results of one forecast run

    `ForecastResult` holds the results of all `Stages <Stage>` from the
    execution of a `ForecastJob`.

    :ivar ISForecastResult is_forecast_result: Result of the induced seismicity
        forecast stage.
    :ivar int hazard_oq_calc_id: Calculation id in the OpenQuake database for
        the record that contains the hazard computation results.
    :ivar int risk_oq_calc_id: Calculation id in the OpenQuake database for
        the record that contains the risk computation results.

    """
    __metaclass__ = DeclarativeQObjectMeta

    # region ORM declarations
    __tablename__ = 'forecast_results'
    id = Column(Integer, primary_key=True)
    hazard_oq_calc_id = Column(Integer)
    risk_oq_calc_id = Column(Integer)
    # Forecast relation
    forecast_id = Column(Integer, ForeignKey('forecasts.id'))
    forecast = relationship('Forecast', back_populates='result')
    # ISModelResult relation
    model_results = relationship('ModelResult', cascade='all, delete-orphan',
                                 back_populates='forecast_result',
                                 collection_class=attribute_mapped_collection(
                                     'model_name'))
    # Scenario relation
    scenarios = relationship('Scenario', back_populates='forecast_results',
                             uselist=False)
    # endregion

    result_changed = QtCore.pyqtSignal(object)

    def commit_changes(self):
        """
        Commit any changes to the database

        Emits the changed signal and persists changes to the database if we
        are within a session

        """
        session = inspect(self).session
        if session:
            session.commit()
        self.result_changed.emit(self)


class Scenario(OrmBase):

    # region ORM declarations
    __tablename__ = 'scenarios'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    # ForecastInput relation
    forecast_inputs_id = Column(Integer, ForeignKey('forecast_inputs.id'))
    forecast_inputs = relationship('ForecastInput', back_populates='scenarios')
    # InjectionPlan relation
    injection_plans = relationship('InjectionPlan',
                                   cascade='all, delete-orphan',
                                   back_populates='scenarios')
    # ForecastResult relation
    forecast_results_id = Column(Integer, ForeignKey('forecast_results.id'))
    forecast_results = relationship('ForecastResult',
                                    back_populates='scenarios')
    # endregion


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
    `cum_result` attribute will contain that value. Some models, such as
    `Shapiro`, have more fine grained spatial resolution. Those store the
    cumulative forecast in `cum_result` and the results for individual voxels
    in `vol_results`.

    :ivar model_name: The name of the model that created the forecast
    :ivar datetime.datetime t_run: Time of the forecast
    :ivar float dt: forecast period duration [hours]
    :ivar bool failed: true if the model did not produce any results
    :ivar str failure_reason: a reason given by the model for not producing any
        results.
    :ivar RatePrediction cum_result: Cumulative forecast result.
    :ivar list[RatePrediction] vol_results: Volumetric results (per voxel)
    :ivar bool reviewed: True if the result has been evaluated against
        measured rates.

    """

    # region ORM declarations
    __tablename__ = 'model_results'
    id = Column(Integer, primary_key=True)
    model_name = Column(String)
    failed = Column(Boolean)
    failure_reason = Column(String)
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
