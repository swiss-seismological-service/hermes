# -*- encoding: utf-8 -*-
# Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED
"""
Defines the class that holds the results of a `ForecastJob` (all stages)


"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, inspect, orm
from sqlalchemy.orm import relationship, backref

from isforecastresult import ISForecastResult
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

    `ForecastResult` holds the results of all `Stages <Stage>` from the
    execution of a `ForecastJob`.

    :param datetime t_run: time of the forecast run
    :ivar datetime t_run: time when the `ForecastJob` was run
    :ivar ISForecastResult is_forecast_result: Result of the induced seismicity
        forecast stage.
    :ivar int hazard_oq_calc_id: Calculation id in the OpenQuake database for
        the record that contains the hazard computation results.
    :ivar int risk_oq_calc_id: Calculation id in the OpenQuake database for
        the record that contains the risk computation results.

    """

    # ORM declarations
    __tablename__ = 'forecastresult'
    id = Column(Integer, primary_key=True)
    t_run = Column(DateTime)
    is_forecast_result_id = Column(Integer, ForeignKey('isforecastresult.id'))
    is_forecast_result = relationship(ISForecastResult.__name__,
                                      cascade='all, delete-orphan',
                                      backref=backref('forecastresult',
                                                      uselist=False),
                                      single_parent=True)
    hazard_oq_calc_id = Column(Integer)
    risk_oq_calc_id = Column(Integer)

    def __init__(self, t_run):
        self.t_run = t_run
        self._mediator = _Mediator()

    @orm.reconstructor
    def _init_on_load(self):
        self._mediator = _Mediator()

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

    @property
    def result_changed(self):
        return self._mediator.result_changed
