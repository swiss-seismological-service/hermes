# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Various utility functions

"""
import abc
import functools

from osgeo import ogr, osr
from PyQt5.QtCore import QTimer, QObject, QDateTime
from sqlalchemy import event


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

    try:
        geom = ogr.CreateGeometryFromWkt(wkt_geom)
    except Exception as err:
        raise ValueError(err)

    if srid is not None:
        try:
            spatial_ref = osr.SpatialReference()
            spatial_ref.ImportFromEPSG(srid)

            geom.AssignSpatialReference(spatial_ref)
        except Exception as err:
            raise ValueError(f'While assigning SRID parameter: {err}')

    geom.CloseRings()

    if (geom.GetGeometryName() != 'POLYHEDRALSURFACE' or  # noqa
        geom.GetGeometryCount() != 6 or not
            is_cuboid_xyz(geom)):
        return False

    return True


def datetime_to_qdatetime(dt):
    """
    Convert a :py:class:`datetime.datetime` object into a corresponding
    :py:class:`PyQt5.QtCore.QDateTime` object.

    :param dt: Datetime to be converted
    :type dt: :py:class:`datetime.datetime`
    
    :rtype: :py:class:`PyQt5.QtCore.QDateTime`
    """
    return QDateTime.fromMSecsSinceEpoch(int(dt.timestamp() * 1000))


def rsetattr(obj, attr, val):
    """
    Recursive setattr variant

    A plugin replacement for the built in `setattr` that allows to set nested
    attributes with dot separation:

        rsetattr(employee, 'address.street.number', '5a')

    """
    pre, _, post = attr.rpartition('.')
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)


def rgetattr(obj, attr, *args):
    """
    Recursive getattr variant

    A plugin replacement for the built in `getattr` that allows to get nested
    attributes with dot separation:

        street_number = rgetattr(employee, 'address.street.number')

    """
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)
    return functools.reduce(_getattr, [obj] + attr.split('.'))


def call_later(method, *args, **kwargs):
    """
    Invokes a method after finishing the current Qt run loop

    :param callable method: Method to invoke
    :param args: Positional args to pass to method
    :param kwargs: Keyword args to pass to method
    """
    QTimer.singleShot(0, functools.partial(method, *args, **kwargs))


class QtABCMeta(type(QObject), abc.ABCMeta):
    pass
