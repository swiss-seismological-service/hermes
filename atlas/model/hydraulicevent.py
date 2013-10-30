# -*- coding: utf-8 -*-
"""
Provides SeismicEvent, a class to represent a seismic event

"""

from sqlalchemy import Column, Integer, Float, DateTime
from datamodel import DataModel
import location
import collections

HydraulicEventData = collections.namedtuple('HydraulicEventData',
                                            'flow_dh flow_xt flow_in'
                                            'pressure_dh pressure_xt'
                                            'constant')



class HydraulicEvent(DataModel):
    """Represents a hydraulic event (change in fluxrate or pressure)

    :ivar date_time: Date and time when the event occurred
    :type date_time: datetime
    :ivar flow_dh: TODO: ?
    :type flow_dh: float
    :ivar flow_xt: TODO: ?
    :type flow_xt: float
    :ivar pressure_dh: TODO: ?
    :type pressure_dh: float
    :ivar pressure_xt: TODO: ?
    :type pressure_xt: float
    :ivar flow_in: TODO: ?
    :type flow_in: float
    :ivar constant: TODO: ?
    :type constant: float

    """

    # ORM declarations
    __tablename__ = 'hydraulicevents'
    id = Column(Integer, primary_key=True)
    date_time = Column(DateTime)
    flow_dh = Column(Float)
    flow_xt = Column(Float)
    pressure_dh = Column(Float)
    pressure_xt = Column(Float)
    flow_in = Column(Float)
    constant = Column(Float)

    def __init__(self, date_time, data):
        """
        :param date_time: Date and time when the event occurred
        :type date_time: datetime
        :param data: Event data as a dictionary containing
        :type data: HydraulicEventData

        """
        self.date_time = date_time
        self.flow_dh = data['flow_dh']
        self.flow_xt = data['flow_xt']
        self.pressure_dh = data['pressure_dh']
        self.pressure_xt = data['pressure_xt']
        self.flow_in = data['flow_in']
        self.constant = data['constant']

    def __str__(self):
        return "Flow: %.1f @ %s" % (self.flow_dh, self.date_time.ctime())

    def __repr__(self):
        return "<HydraulicEvent('%s' @ '%s')>" % (self.flow_dh, self.date_time)