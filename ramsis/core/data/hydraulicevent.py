# -*- coding: utf-8 -*-
# Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""
Defines the `HydraulicEvent` class.

Hydraulic events are the samples that are recorded
at the borehole sensors to measure injection pressure and flow rate.

"""

from sqlalchemy import Column, Integer, Float, DateTime
from ormbase import OrmBase


class HydraulicEvent(OrmBase):
    """
    Represents a hydraulic event (i.e. a flowrate and pressure)

    :ivar datetime.datetime date_time: Date and time when the event occurred
    :ivar float flow_dh: Flow downhole [l/min]
    :ivar float float flow_xt: Flow @ x-mas tree (top hole) [l/min]
    :ivar float pr_dh: pressure downhole [bar]
    :ivar float pr_xt: pressure @ x-mas tree (top hole) [bar]

    """

    # ORM declarations
    __tablename__ = 'hydraulicevents'
    id = Column(Integer, primary_key=True)
    date_time = Column(DateTime)
    flow_dh = Column(Float)
    flow_xt = Column(Float)
    pr_dh = Column(Float)
    pr_xt = Column(Float)

    # Data attributes (required for flattening)
    data_attrs = ['date_time', 'flow_dh', 'flow_xt', 'pr_dh', 'pr_xt']

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
