# -*- coding: utf-8 -*-
"""
Provides HydraulicEvent, a class to represent hydraulic events

"""

from sqlalchemy import Column, Integer, Float, DateTime
from datamodel import DataModel


class HydraulicEvent(DataModel):
    """Represents a hydraulic event (change in fluxrate or pressure)

    :ivar date_time: Date and time when the event occurred
    :type date_time: datetime
    :ivar flow_dh: flow downhole [l/min]
    :type flow_dh: float
    :ivar flow_xt: flow @ x-mas tree (top hole) [l/min]
    :type flow_xt: float
    :ivar pressure_dh: pressure downhole [bar]
    :type pressure_dh: float
    :ivar pressure_xt: pressure @ x-mas tree (top hole) [bar]
    :type pressure_xt: float

    """

    # ORM declarations
    __tablename__ = 'hydraulicevents'
    id = Column(Integer, primary_key=True)
    date_time = Column(DateTime)
    flow_dh = Column(Float)
    flow_xt = Column(Float)
    pr_dh = Column(Float)
    pr_xt = Column(Float)

    def __init__(self, date_time, flow_dh, flow_xt, pr_dh, pr_xt):
        """
        The initialisation parameters are the same as the member variables.
        See class description for details.

        """
        self.date_time = date_time
        self.flow_dh = flow_dh
        self.flow_xt = flow_xt
        self.pr_dh = pr_dh
        self.pr_xt = pr_xt

    def __str__(self):
        return "Flow: %.1f @ %s" % (self.flow_dh, self.date_time.ctime())

    def __repr__(self):
        return "<HydraulicEvent('%s' @ '%s')>" % (self.flow_dh, self.date_time)

    def __eq__(self, other):
        if isinstance(other, HydraulicEvent):
            same = (self.date_time == other.date_time and
                    self.flow_dh == other.flow_dh and
                    self.flow_xt == other.flow_xt and
                    self.pr_dh == other.pr_dh and
                    self.pr_xt == other.pr_xt)
            return same
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        else:
            return not result