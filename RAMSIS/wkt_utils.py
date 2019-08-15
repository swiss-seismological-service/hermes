# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Utilities for working with Well Known Text / Binary (WKT, WKB) from
GeoAlchemy2

"""

import binascii

from gdal import ogr
from geoalchemy2.elements import WKBElement


# Methods to parse WKT / WKB

def coordinates_from_wkb(wkb_element):
    """  Returns the coordinates for a POINTZ WKBElement as a list """
    if wkb_element is None:
        return []
    wkb = binascii.unhexlify(wkb_element.desc.encode('utf-8'))
    p = ogr.CreateGeometryFromWkb(wkb)
    return [p.GetX(), p.GetY(), p.GetZ()]


# Methods to create WKT / WKB representations

def coordinates_to_wkb(coordinates):
    """ Converts a list of coordinates to POINT WKBElement """
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(*coordinates)
    return WKBElement(point.ExportToWkb())
