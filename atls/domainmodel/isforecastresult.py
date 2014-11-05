# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import logging
from sqlalchemy import Column, Integer, Float, DateTime, Boolean, String, \
    Interval, ForeignKey
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm import relationship
from isha.common import ModelOutput, ModelResult
from datamodel import DataModel
from modelvalidation import log_likelihood


class ISForecastResult(DataModel):
    """
    Results of one IS forecast run

    """

    # ORM declarations
    __tablename__ = 'isforecastresults'
    id = Column(Integer, primary_key=True)
    t_run = Column(DateTime)
    _reviewed = Column('reviewed', Boolean)
    model_results = relationship('ISModelResult', backref='isforecastresult',
        collection_class=attribute_mapped_collection('model_name'),
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
        return self._reviewed

    def review(self, observed_events):
        for result in self.model_results.itervalues():
            result.review(observed_events)
        self._reviewed = True


class ISModelResult(DataModel):
    """
    Output resulting from IS forecast run for one specific IS model. The output
    either contains a result or a reason why no result is available.

    :ivar model_name: a reference to the model that created the forecast
    :ivar t_run: time of the forecast
    :type t_run: datetime
    :ivar dt: forecast period duration [hours]
    :type dt: timedelta
    :ivar failed: true if the model did not produce any results
    :ivar failure_reason: a reason given by the model for not producing any
        results.
    :ivar cum_result: cumulative forecast result
    :type cum_result: ISResult
    :ivar vol_results: volumetric results (per voxel)
    :type vol_results: list[ISResult]

    """

    # ORM declarations
    __tablename__ = 'ismodelresults'
    id = Column(Integer, primary_key=True)
    model_name = Column(String)
    failed = Column(Boolean)
    failure_reason = Column(String)
    t_run = Column(DateTime)
    dt = Column(Interval)

    # Configures the one-to-one relationship for the cumulative result
    # use_alter=True along with name='' adds this foreign key after ISResult
    # has been created to avoid circular dependency
    cum_result_id = Column(Integer, ForeignKey('isresult.id', use_alter=True,
                                               name='fk_cum_result_id'))
    # set post_update=True to avoid circular dependency during
    cum_result = relationship('ISResult', foreign_keys=cum_result_id,
                              post_update=True)

    forecast_id = Column(Integer, ForeignKey('isforecastresults.id'))
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
            self.vol_results = None

    @property
    def reviewed(self):
        return self._reviewed

    def compute_cumulative(self):
        """
        Computes the cumulative result from the individual spatial results.

        """
        rate = reduce(lambda x, y: x+y,
                      [r.review for r in self.vol_results])
        prob = reduce(lambda x, y: x+y,
                      [r.prob for r in self.vol_results])
        self.cum_result = ISResult(rate, prob)

    def review(self, observations):
        """
        Reviews results based on the 'truth' data in event **observations** for
        the forecast period and assigns a score to the model.

        :param observations: the observed events for the forecast period
        :type observations: list of SeismicEvent objects

        """
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        if self.vol_results is not None:
            # TODO: compute LL per voxel
            # at the moment we don't know the region for each volumetric
            # result.
            #for result in self.vol_results:
            #    region = result.region
            #    obs = len([e for e in observations if e.in_region(region)])
            #    result.score = log_likelihood(result.review, obs)
            pass
        self.cum_result.score = log_likelihood(self.cum_result.rate,
                                               len(observations))
        self._reviewed = True
        logger.debug('{} at {}: LL = {}'.format(self.model.title,
                                                self.t_run,
                                                self.result.score.LL))


class ISResult(DataModel):
    """ Result container for a single forecast """

    # ORM declarations
    __tablename__ = 'isresults'
    id = Column(Integer, primary_key=True)
    rate = Column(Float)
    prob = Column(Float)
    score = Column(Float)

    # Configures the one-to-many relationship between ISModelResult's
    # vol_results and this entity
    model_result_id = Column(Integer, ForeignKey(ISModelResult.id))
    model_result = relationship(ISModelResult, foreign_keys=model_result_id,
                                backref='vol_results')

    def __init__(self, rate, prob):
        self.prob = prob
        self.rate = rate
        self.score = None

    @classmethod
    def from_model_result(cls, result):
        """
        Inits an ISResult from a bare model result

        :param result: model result
        :type result: ModelResult

        """
        return cls(result.rate, result.prob)
