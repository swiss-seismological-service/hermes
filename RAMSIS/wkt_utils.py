# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Utilities for working with Well Known Text / Binary (WKT, WKB)

"""

from geoalchemy2.shape import to_shape, from_shape
from geoalchemy2.elements import WKBElement, WKTElement
from shapely.geometry import Point


# Methods to parse WKT / WKB

def coordinates_from_wkb_point(wkt):
    """  Returns the coordinates for POINT wkb or wkt as a list """
    if isinstance(wkt, (WKTElement, WKBElement)):
        point = to_shape(wkt)
        if isinstance(point, Point):
            return point.coords[0]
    return []


# Methods to create WKT / WKB representations

def coordinates_to_wkb_point(coordinates, srid=4326):
    """ Converts a list of coordinates to POINT wkb """
    point = Point(coordinates)
    return from_shape(point, srid)

