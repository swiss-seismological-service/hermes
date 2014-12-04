# -*- encoding: utf-8 -*-
"""
Forecast results
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import logging

from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref

from ormbase import OrmBase
from PyQt4 import QtCore


class _Mediator(QtCore.QObject):
    """
    PyQt 4 doesn't support multiple inheritance, thus we use a mediator class
    to handle signals

    """
    result_changed = QtCore.pyqtSignal(object)


class ForecastResult(OrmBase):
    """
    Results of one forecast run

    ForecastResult holds the results from a forecast run including the IS
    forecast, hazard and risk results

    """

    # ORM declarations
    __tablename__ = 'forecastresult'
    id = Column(Integer, primary_key=True)
    t_run = Column(DateTime)
    is_forecast_result_id = Column(Integer, ForeignKey('isforecastresult.id'))
    is_forecast_result = relationship('ISForecastResult',
                                      cascade='all, delete-orphan',
                                      backref=backref('forecastresult',
                                                      uselist=False),
                                      single_parent=True)
    hazard_oq_calc_id = Column(Integer)
    risk_oq_calc_id = Column(Integer)

    def __init__(self, t_run):
        """
        :param t_run: time of the model run
        :type t_run: datetime

        """
        self.t_run = t_run
        self._mediator = _Mediator()

    @property
    def result_changed(self):
        return self._mediator.result_changed