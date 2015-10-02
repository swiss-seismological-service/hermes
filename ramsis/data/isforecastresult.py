# -*- encoding: utf-8 -*-
# Copyright (C) 2013, SED (ETH Zurich) and Geo-Energie Suisse AG

"""
Classes that store results for induced seismicity forecasts (i.e. the
`ISForecastStage` of `ForecastJob`) and methods to analyse those results.

The following graph shows the relationship between the classes in this module:

.. graphviz::

   graph results {
      "ISForecastResult" [xlabel="IS stage results (all models)"];
      "ISResult-c" [shape=box, label="ISResult"];
      "ISResult-v" [shape=box, label="ISResult", xlabel="Computed values"];
      "ISModelResult" [shape=box, xlabel="Single model results"];
      "ISForecastResult" -- "ISModelResult" [label="model_results",
          headlabel="1"];
      "ISModelResult" -- "ISResult-c" [label="cum_result", headlabel="1"];
      "ISModelResult" -- "ISResult-v" [label="vol_results", headlabel="*"];
   }

"""

import logging
from math import log, factorial

from sqlalchemy import Column, Integer, Float, DateTime, Boolean, String, \
    ForeignKey
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm import relationship, backref

from ormbase import OrmBase


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


class ISForecastResult(OrmBase):
    """
    Top level results container for IS forecasts.

    `ISForecastResult` stores the results of all `Models <Model>` in
    ``model_results``. The attribute ``model_results`` is a list of
    `ISModelResult` objects.

    :ivar bool reviewed: True if the result has been evaluated against
        measured rates.

    """

    # ORM declarations
    __tablename__ = 'isforecastresult'
    id = Column(Integer, primary_key=True)
    t_run = Column(DateTime)
    _reviewed = Column('reviewed', Boolean)
    model_results = relationship('ISModelResult', backref='isforecastresult',
                                 collection_class=attribute_mapped_collection(
                                     'model_name'),
                                 cascade="all, delete-orphan")

    def __init__(self, t_run):
        """
        :param t_run: time of the model run
        :type t_run: datetime

        """
        self.t_run = t_run
        self._reviewed = False
        self.model_results = {}

    @property
    def reviewed(self):
        """
        True if the forecast result has been evaluated against real measured
        seismicity rates through `review`.

        """
        return self._reviewed

    def review(self, observed_events):
        """
        Compare forecasted rate against observed rate of seismicity.

        :param list[SeismicEvent] observed_events: Observed seismic events

        """
        for result in self.model_results.itervalues():
            result.review(observed_events)
        self._reviewed = True


class ISModelResult(OrmBase):
    """
    Result from a single forecast `Model` The result either contains actual
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
    :ivar ISResult cum_result: Cumulative forecast result.
    :ivar list[ISResult] vol_results: Volumetric results (per voxel)
    :ivar bool reviewed: True if the result has been evaluated against
        measured rates.

    """

    # ORM declarations
    __tablename__ = 'ismodelresult'
    id = Column(Integer, primary_key=True)
    model_name = Column(String)
    failed = Column(Boolean)
    failure_reason = Column(String)
    t_run = Column(DateTime)
    dt = Column(Float)

    # Configures the one-to-one relationship for the cumulative result
    # use_alter=True along with name='' adds this foreign key after ISResult
    # has been created to avoid circular dependency
    cum_result_id = Column(Integer, ForeignKey('isresult.id', use_alter=True,
                                               name='fk_cum_result_id'))
    # set post_update=True to avoid circular dependency during
    cum_result = relationship('ISResult', foreign_keys=cum_result_id,
                              post_update=True, cascade="all, delete-orphan",
                              single_parent=True)

    forecast_id = Column(Integer, ForeignKey('isforecastresult.id'))
    _reviewed = Column('reviewed', Boolean)

    def __init__(self, output):
        """
        Inits an ISModelResult from a bare ModelOutput

        :param output: model output
        :type output: ModelOutput

        """
        self.model_name = output.model.title
        self.failed = output.failed
        self.failure_reason = output.failure_reason
        self.t_run = output.t_run
        self.dt = output.dt
        if output.cum_result is not None:
            self.cum_result = ISResult.from_model_result(output.cum_result)
        else:
            self.cum_result = None
        if output.vol_results is not None:
            self.vol_results = [ISResult.from_model_result(r)
                                for r in output.vol_results]
        else:
            self.vol_results = []

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
        self.cum_result = ISResult(rate, b_val, prob)

    def review(self, observations):
        """
        Reviews results based on the 'truth' data in event **observations** for
        the forecast period and assigns a score to the model.

        :param observations: the observed events for the forecast period
        :type observations: list of SeismicEvent objects

        """
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        if self.vol_results:
            # TODO: compute LL per voxel
            # at the moment we don't know the region for each volumetric
            # result.
            # for result in self.vol_results:
            #     region = result.region
            #     obs = len([e for e in observations if e.in_region(region)])
            #     result.score = log_likelihood(result.review, obs)
            pass
        self.cum_result.score = log_likelihood(self.cum_result.rate,
                                               len(observations))
        self._reviewed = True
        logger.debug('{} at {}: LL = {}'.format(self.model.title,
                                                self.t_run,
                                                self.result.score.LL))


class ISResult(OrmBase):
    """
    Result container for a single forecasted seismic rate

    :ivar float rate: Forecasted seismicity rate
    :ivar float b_val: Expected b value
    :ivar float prob: Expected probability of exceedance
    :ivar score: Score (log-likelihood value) of the forecast after review
    :ivar model_result: Reference to the model result that this result belongs
        to.

    """

    # ORM declarations
    __tablename__ = 'isresult'
    id = Column(Integer, primary_key=True)
    rate = Column(Float)
    b_val = Column(Float)
    prob = Column(Float)
    score = Column(Float)

    # Configures the one-to-many relationship between ISModelResult's
    # vol_results and this entity
    model_result_id = Column(Integer, ForeignKey(ISModelResult.id))
    model_result = relationship(ISModelResult,
                                foreign_keys=model_result_id,
                                backref=backref('vol_results',
                                cascade="all, delete-orphan"))

    def __init__(self, rate, b_val, prob):
        self.prob = prob
        self.rate = rate
        self.b_val = b_val
        self.score = None

    @classmethod
    def from_model_result(cls, result):
        """
        Convenience initializer to init an ISResult from a bare model result

        :param result: model result
        :type result: ModelResult

        """
        return cls(result.rate, result.b_val, result.prob)
