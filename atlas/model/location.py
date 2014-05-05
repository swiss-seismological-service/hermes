# -*- encoding: utf-8 -*-
"""
Provides Locaiton, a class to store geographic locations

"""


class Location(object):
    """ Represents a location in terms of longitude, latitude, and altitude

    Altitude is positive upwards, with 0 being the earth's surface

    :param longitude: Longitude, in decimal degrees.
    :type longitude: float
    :param latitude: Latitude, in decimal degrees.
    :type latitude: float
    :param altitude: Altitude (default: 0.0), in m (positive upwards)
    :type altitude: float

    """

    def __init__(self, longitude, latitude, altitude=0.0):
        """
        Altitude is positive upwards, with 0 being the earth's surface

        :param longitude: Longitude, in decimal degrees.
        :type longitude: float
        :param latitude: Latitude, in decimal degrees.
        :type latitude: float
        :param altitude: Altitude (default: 0.0), in m (positive upwards)
        :type altitude: float

        """
        # TODO: add range check
        self.longitude = longitude
        self.latitude = latitude
        self.altitude = altitude