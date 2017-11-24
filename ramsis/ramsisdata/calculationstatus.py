# -*- encoding: utf-8 -*-
"""
Processing status of models and hazard and risk stages

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import json
from datetime import datetime
from sqlalchemy import Column, Integer, event, DateTime, String, PickleType,\
    ForeignKey
from sqlalchemy.orm import relationship, Session
from .ormbase import OrmBase


@event.listens_for(Session, 'after_flush')
def delete_status_orphans(session, ctx):
    """
    CalculationStatus orphan deletion

    Status can have different kinds of parents, so a simple 'delete-orphan' 
    statement on the relation doesn't work. Instead we check after each flush 
    to the db if there are any orphaned status and delete them if necessary.

    :param Session session: The current session

    """
    if any(isinstance(i, CalculationStatus) for i in session.dirty):
        query = session.query(CalculationStatus).\
                filter_by(model_result=None, hazard_result=None,
                          risk_result=None)
        orphans = query.all()
        for orphan in orphans:
            session.delete(orphan)


class CalculationStatus(OrmBase):
    """
    Calculation status of the hazard or risk stage of forecast models
    
    The info dict contains zero or more of the following fields by
    convention:
    
    info = {
        'last_response': Last http response for remote workers
    }
    
    """

    # Defined states
    PENDING = 'Pending'
    RUNNING = 'Running'
    ERROR = 'Error'
    COMPLETE = 'Complete'

    # region ORM Declarations
    __tablename__ = 'calculation_status'
    id = Column(Integer, primary_key=True)
    calc_id = Column(PickleType(pickler=json))  # identifies the calculation
    state = Column(String)        # A defined state or None
    date = Column(DateTime)       # Date and time of the state
    info = Column(PickleType(pickler=json))     # Additional information as a dict or string
    # relationships, only one of those is used for each
    model_result_id = Column(Integer, ForeignKey('model_results.id'))
    model_result = relationship('ModelResult', back_populates='status')
    hazard_result_id = Column(Integer, ForeignKey('hazard_results.id'))
    hazard_result = relationship('HazardResult', back_populates='status')
    risk_result_id = Column(Integer, ForeignKey('risk_results.id'))
    risk_result = relationship('RiskResult', back_populates='status')
    # endregion

    @property
    def finished(self):
        return True if self.state in (self.ERROR, self.COMPLETE) else False

    def __init__(self, calc_id, state=None, info=None):
        self.calc_id = calc_id
        self.state = state if state else self.PENDING
        self.info = info
        self.date = datetime.utcnow()


