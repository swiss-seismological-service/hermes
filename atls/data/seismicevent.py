# -*- coding: utf-8 -*-
"""
Provides SeismicEvent, a class to represent a seismic event

"""

from sqlalchemy import Column, Integer, Float, DateTime

from ormbase import OrmBase
from data.geometry import Point


class SeismicEvent(OrmBase):
    """Represents a seismic event

    :ivar date_time: Date and time when the event occurred
    :type date_time: datetime
    :ivar magnitude: Event magnitude
    :type magnitude: float
    :ivar x: Event x coordinate
    :type x: float
    :ivar y: Event y coordinate [m]
    :type y: float
    :ivar z: Event depth [m] (0 at surface, positive downwards)
    :type z: float

    """

    # ORM declarations
    __tablename__ = 'seismicevents'
    id = Column(Integer, primary_key=True)
    magnitude = Column(Float)
    date_time = Column(DateTime)
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)

    # Data attributes (required for flattening)
    data_attrs = ['magnitude', 'date_time', 'x', 'y', 'z']

    def in_region(self, region):
        """
        Tests if the event is located inside **region**

        :param region: Region to test (cube)
        :type region: Cube
        :return: True if the event is inside the region, false otherwise

        """
        return Point(self.x, self.y, self.z).in_cube(region)

    def __init__(self, date_time, magnitude, location):
        """
        :param date_time: Date and time when the event occurred
        :type date_time: datetime.datetime
        :param magnitude: Event magnitude
        :type magnitude: float
        :param location: Event coordinates
        :type location: Point

        """
        self.date_time = date_time
        self.magnitude = magnitude
        self.x = location.x
        self.y = location.y
        self.z = location.z

    def __str__(self):
        return "M%.1f @ %s" % (self.magnitude, self.date_time.ctime())

    def __repr__(self):
        return "<SeismicEvent('%s' @ '%s')>" % (self.magnitude, self.date_time)

    def __eq__(self, other):
        if isinstance(other, SeismicEvent):
            return (self.date_time == other.date_time and
                    self.magnitude == other.magnitude and
                    self.x == other.x and
                    self.y == other.y and
                    self.z == other.z)
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        else:
            return not result