# -*- coding: utf-8 -*-
"""
Provides SeismicEvent, a class to represent a seismic event

"""

from sqlalchemy import Column, Integer, Float, DateTime
from datamodel import DataModel


class SeismicEvent(DataModel):
    """Represents a seismic event

    :ivar date_time: Date and time when the event occurred
    :type date_time: datetime
    :ivar decay_time: The date and time at which the influence of the event on future forecasts becomes insignificant
    :type decay_time: datetime
    :ivar magnitude: Event magnitude
    :type magnitude: float
    :ivar latitude: Event latitude
    :type latitude: float
    :ivar longitude: Event longitude
    :type longitude: float
    :ivar depth: Event depth (0 at surface, positive downwards)
    :type depth: float

    """

    # ORM declarations
    __tablename__ = 'seismicevents'
    id = Column(Integer, primary_key=True)
    magnitude = Column(Float)
    date_time = Column(DateTime)
    decay_time = Column(DateTime)
    latitude = Column(Float)
    longitude = Column(Float)
    depth = Column(Float)

    def __init__(self, date_time, magnitude, location):
        """
        :param date_time: Date and time when the event occurred
        :type date_time: datetime
        :param magnitude: Event magnitude
        :type magnitude: float
        :param location: Event location
        :type location: Location

        """
        self.date_time = date_time
        self.magnitude = magnitude
        self.latitude = location.latitude
        self.longitude = location.longitude
        self.depth = -location.altitude

    def __str__(self):
        return "M%.1f @ %s" % (self.magnitude, self.date_time.ctime())

    def __repr__(self):
        return "<SeismicEvent('%s' @ '%s')>" % (self.magnitude, self.date_time)

    def __cmp__(self, other):
        return self.date_time == other.date_time and \
               self.magnitude == other.magnitude and \
               self.latitude  == other.latitude  and \
               self.longitude == other.longitude and \
               self.depth     == other.depth

