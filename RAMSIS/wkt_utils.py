# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Utilities for working with Well Known Text / Binary (WKT, WKB) from
GeoAlchemy2

"""

import binascii

from osgeo import ogr
from geoalchemy2.elements import WKBElement


def is_phsf(wkt_geom, srid=None):
    """
    Validate the reservoir geometry and check if the passed geometry
    corresponds to a *Polyhedralsurface*.

    :param str wkt_geom: Reservoir geometry description in WKT format.
    :param srid: Optional spatial reference identifier
    :type srid: int or None

    :returns: :code:`True` if :code:`wkt_geom` is a valid
        Polyhedralsurface, else :code:`False`
    :rtype: bool
    """

    def is_cuboid_xyz(geom):
        """
        Check if a a :code:`POLYHEDRALSURFACE` is cube-/cuboid-like in the
        xyz-plane

        :param geom: Geometry to be checked
        :type geom: :py:class:`osgeo.ogr.Geometry`

        :returns: :code:`True` if the geomentry is cube-/cuboid-like
        :rtype: bool
        """
        geom_env = geom.GetEnvelope3D()
        min_x = geom_env[0]
        max_x = geom_env[1]
        min_y = geom_env[2]
        max_y = geom_env[3]
        min_z = geom_env[4]
        max_z = geom_env[5]

        # define corner coordinates
        c0 = min_x, min_y, min_z
        c1 = min_x, max_y, min_z
        c2 = max_x, max_y, min_z
        c3 = max_x, min_y, min_z
        c4 = min_x, min_y, max_z
        c5 = min_x, max_y, max_z
        c6 = max_x, max_y, max_z
        c7 = max_x, min_y, max_z

        phsf = ogr.Geometry(ogr.wkbPolyhedralSurfaceZ)

        r0 = ogr.Geometry(ogr.wkbLinearRing)
        r0.AddPoint(*c0)
        r0.AddPoint(*c1)
        r0.AddPoint(*c2)
        r0.AddPoint(*c3)
        r0.AddPoint(*c0)
        p0 = ogr.Geometry(ogr.wkbPolygon)
        p0.AddGeometry(r0)
        phsf.AddGeometry(p0)

        r1 = ogr.Geometry(ogr.wkbLinearRing)
        r1.AddPoint(*c0)
        r1.AddPoint(*c1)
        r1.AddPoint(*c5)
        r1.AddPoint(*c4)
        r1.AddPoint(*c0)
        p1 = ogr.Geometry(ogr.wkbPolygon)
        p1.AddGeometry(r1)
        phsf.AddGeometry(p1)

        r2 = ogr.Geometry(ogr.wkbLinearRing)
        r2.AddPoint(*c0)
        r2.AddPoint(*c3)
        r2.AddPoint(*c7)
        r2.AddPoint(*c4)
        r2.AddPoint(*c0)
        p2 = ogr.Geometry(ogr.wkbPolygon)
        p2.AddGeometry(r2)
        phsf.AddGeometry(p2)

        r3 = ogr.Geometry(ogr.wkbLinearRing)
        r3.AddPoint(*c6)
        r3.AddPoint(*c7)
        r3.AddPoint(*c4)
        r3.AddPoint(*c5)
        r3.AddPoint(*c6)
        p3 = ogr.Geometry(ogr.wkbPolygon)
        p3.AddGeometry(r3)
        phsf.AddGeometry(p3)

        r4 = ogr.Geometry(ogr.wkbLinearRing)
        r4.AddPoint(*c6)
        r4.AddPoint(*c7)
        r4.AddPoint(*c3)
        r4.AddPoint(*c2)
        r4.AddPoint(*c6)
        p4 = ogr.Geometry(ogr.wkbPolygon)
        p4.AddGeometry(r4)
        phsf.AddGeometry(p4)

        r5 = ogr.Geometry(ogr.wkbLinearRing)
        r5.AddPoint(*c6)
        r5.AddPoint(*c2)
        r5.AddPoint(*c1)
        r5.AddPoint(*c5)
        r5.AddPoint(*c6)
        p5 = ogr.Geometry(ogr.wkbPolygon)
        p5.AddGeometry(r5)
        phsf.AddGeometry(p5)

        return phsf.Equals(geom)

    geom = ogr.CreateGeometryFromWkt(wkt_geom)
    if geom is None:
        return False

    geom.CloseRings()

    if (geom.GetGeometryName() != 'POLYHEDRALSURFACE' or
        geom.GetGeometryCount() != 6 or not
            is_cuboid_xyz(geom)):
        return False

    return True


def point_to_proj4(wkb_point):
    """
    Return a *pseudo* PROJ4 string from a point.

    :param wkb_point: Point to convert
    :type wkb_point: :py:class:`geoalchemy2.elements.WKBElement`
    """
    if wkb_point is None:
        return ''

    c = coordinates_from_wkb(wkb_point)
    return f'+x_0={c[0]} +y_0={c[1]} +z_0={c[2]}'


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


def wkb_to_wkt(wkb_element):
    """
    Convert a :code:`WKBElement` to the corresponding WKT representation.
    """
    wkb = binascii.unhexlify(wkb_element.desc.encode('utf-8'))
    return ogr.CreateGeometryFromWkb(wkb).ExportToWkt()
