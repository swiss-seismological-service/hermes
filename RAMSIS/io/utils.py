# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
General purpose IO utilities.
"""

import abc
import contextlib
import functools
import io
import logging

import pymap3d
import requests

from urllib.parse import urlparse, urlunparse

from marshmallow import fields, validate
from osgeo import ogr, osr

from ramsis.utils.error import Error


def validate_positive(d):
    return d >= 0


validate_percentage = validate.Range(min=0, max=100)

DateTime = functools.partial(fields.DateTime, format='%Y-%m-%dT%H:%M:%S.%f')
Percentage = functools.partial(fields.Float, validate=validate_percentage)
Positive = functools.partial(fields.Float, validate=validate_positive)
Uncertainty = Positive


class _IOError(Error):
    """Base IO error ({})."""


class InvalidProj4(_IOError):
    """Invalid Proj4 projection specified: {}"""


class TransformationError(_IOError):
    """Error while performing CRS transformation: {}"""


# NOTE(damb): RequestError instances carry the response, too.
class RequestsError(requests.exceptions.RequestException, _IOError):
    """Base request error ({})."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class NoContent(RequestsError):
    """The request '{}' is returning no content ({})."""


class ClientError(RequestsError):
    """Response code not OK ({})."""


# -----------------------------------------------------------------------------
class IOBase(abc.ABC):
    """
    Abstract IO base class
    """
    LOGGER = 'ramsis.io.io'

    def __init__(self, **kwargs):
        self.logger = logging.getLogger(self.LOGGER)

        self._proj = kwargs.get('proj', None)
        self._transform_callback = _callable_or_raise(
            kwargs.get('transform_callback', self._transform))

    @property
    def proj(self):
        return self._proj

    def transform_callback(self, func):
        """
        Decorator that registers a custom SRS transformation.

        The function should receive the coordinates :code:`x`, :code:`y,
        :code:`z`, and an optional projection. The function is required to
        return a tuple of the transformed values.  Overrides the deserializer's
        :code:`_transform` method.

        :param callable func: The SRS transformation to be registered

        The usage is illustrated bellow:

        .. code::

            deserializer = QuakeMLDeserializer(proj=proj)

            @deserializer.transform_callback
            def crs_transform(x, y, z, proj):
                return pymap3d_transform(x, y, z, proj)

            cat = deserializer.load(data)
        """
        self._transform_callback = _callable_or_raise(func)
        return func

    @staticmethod
    def _transform(x, y, z, source_proj, target_proj):
        """
        Utility method performing a spatial transformation relying on `GDAL's
        Python API <https://pypi.org/project/GDAL/>`.

        :param float x: X value
        :param float y: Y value
        :param float z: Z value
        :param source_proj: Source CRS description (PROJ4 or EPSG)
        :type source_proj: int or str
        :param target_proj: Target CRS description (PROJ4 or EPSG)
        :type target_proj: int or str

        :returns: Transformed values
        :rtype: tuple
        """
        source_srs = osr.SpatialReference()
        if isinstance(source_proj, int):
            source_srs.ImportFromEPSG(source_proj)
        elif isinstance(source_proj, str):
            source_srs.ImportFromProj4(source_proj)
        else:
            raise ValueError(f"Invalid value passed {source_proj!r}")

        target_srs = osr.SpatialReference()
        if isinstance(target_proj, int):
            target_srs.ImportFromEPSG(target_proj)
        elif isinstance(target_proj, str):
            target_srs.ImportFromProj4(target_proj)
        else:
            raise ValueError(f"Invalid value passed {target_proj!r}")

        t = osr.CoordinateTransformation(source_srs, target_srs)
        # convert to WKT
        point_z = ogr.CreateGeometryFromWkt(f"POINT_Z ({x} {y} {z})")
        point_z.Transform(t)

        return point_z.GetX(), point_z.GetY(), point_z.GetZ()


class SerializerBase(abc.ABC):
    """
    Abstract base class for serializers.
    """

    @abc.abstractmethod
    def _serialize(self, data):
        pass

    def dumps(self, data):
        """
        Serialize to string. Alias for :py:meth:`_serialize`.

        :param data: Data to be serialized.
        """
        return self._serialize(data)

    def _dumpo(self, data):
        """
        Serialize to :code:`dict`.

        :param data: Data to be serialized.

        :rtype: dict
        """
        raise NotImplementedError


class DeserializerBase(abc.ABC):
    """
    Abstract base class for deserializers.
    """

    @abc.abstractmethod
    def _deserialize(self):
        pass

    def load(self, ifd):
        """
        Deserialize data from a file-like object (i.e. must support
        :code:`.read()`).
        """
        return self._deserialize(ifd.read())

    def loads(self, data):
        """
        Deserialize :code:`data` from string.

        :param data: Data to be deserialized.
        :type data: str or bytes
        """
        return self._deserialize(data)

    def _loado(self, data):
        """
        Deserialize :code:`data` from an object.

        :param data: Data to be deserialized.
        """
        raise NotImplementedError


# -----------------------------------------------------------------------------
@contextlib.contextmanager
def binary_request(request, url, params={}, timeout=None, **kwargs):
    """
    Make a binary request

    :param request: Request object to be used
    :type request: :py:class:`requests.Request`
    :param str url: URL
    :params dict params: Dictionary of query parameters
    :param timeout: Request timeout
    :type timeout: None or int or tuple

    :rtype: io.BytesIO

    :raises: :code:`ValueError` for an invalid :code:`url`
    """
    def validate_args(url, params):
        _url = urlparse(url)

        if _url.params or _url.query or _url.fragment:
            raise ValueError(f"Invalid URL: {url}")

        return urlunparse(_url), params

    url, params = validate_args(url, params)

    try:
        r = request(url, params=params, timeout=timeout, **kwargs)
        # TODO(damb): Move codes to a generic settings variable
        if r.status_code in (204, 404):
            raise NoContent(r.url, r.status_code, response=r)

        r.raise_for_status()
        if r.status_code != 200:
            raise ClientError(r.status_code, response=r)

        yield io.BytesIO(r.content)

    except (NoContent, ClientError) as err:
        raise err
    except requests.exceptions.RequestException as err:
        raise RequestsError(err, response=err.response)


def _callable_or_raise(obj):
    """
    Makes sure an object is callable if it is not :code:`None`.

    :returns: Object validated
    :raises: code:`ValueError` if :code:`obj` is not callable
    """
    if obj and not callable(obj):
        raise ValueError(f"{obj!r} is not callable.")
    return obj


def pymap3d_transform_geodetic2ned(x, y, z, source_proj, target_proj):
    """
    Utility method performing a spatial transformation relying on `pymap3d's
    <https://github.com/scivision/pymap3d>` :code:`geodetic2ned` function.

    :param float x: X value
    :param float y: Y value
    :param float z: Z value
    :param source_proj: Source CRS description (PROJ4 or EPSG)
    :type source_proj: int or str
    :param target_proj: Target CRS description (PROJ4)
    :type target_proj: str

    :returns: Transformed values
    :rtype: tuple
    """
    if source_proj not in (4326, '+proj=longlat +datum=WGS84 +no_defs'):
        raise ValueError(
            'Only WGS84 source projections handled (EPSG, PROJ4).')
    if not isinstance(target_proj, str):
        raise ValueError('Only PROJ4 target projection handled.')

    # extract observer position from proj4 string
    origin = dict([v.split('=') for v in target_proj.split(' ')
                   if (v.startswith('+x_0') or
                       v.startswith('+y_0') or
                       v.startswith('+z_0'))])

    if len(origin) != 3:
        raise ValueError(f"Invalid proj4 string: {target_proj!r}")

    n, e, d = pymap3d.geodetic2ned(
        y, x, z,
        float(origin['+y_0']), float(origin['+x_0']), float(origin['+z_0']))
    return e, n, d


def pymap3d_transform_ned2geodetic(x, y, z, source_proj, target_proj):
    """
    Utility method performing a spatial transformation relying on `pymap3d's
    <https://github.com/scivision/pymap3d>` :code:`ned2geodetic` function.

    :param float x: X value
    :param float y: Y value
    :param float z: Z value
    :param source_proj: Source CRS description (PROJ4 or EPSG)
    :type source_proj: int or str
    :param target_proj: Target CRS description (PROJ4)
    :type target_proj: str

    :returns: Transformed values
    :rtype: tuple
    """
    if target_proj not in (4326, '+proj=longlat +datum=WGS84 +no_defs'):
        raise ValueError(
            'Only WGS84 source projections handled (EPSG, PROJ4).')
    if not isinstance(source_proj, str):
        raise ValueError('Only PROJ4 target projection handled.')

    # extract observer position from proj4 string
    origin = dict([v.split('=') for v in source_proj.split(' ')
                   if (v.startswith('+x_0') or
                       v.startswith('+y_0') or
                       v.startswith('+z_0'))])

    if len(origin) != 3:
        raise ValueError(f"Invalid proj4 string: {source_proj!r}")

    lat, lon, alt = pymap3d.ned2geodetic(
        y, x, z,
        float(origin['+y_0']), float(origin['+x_0']), float(origin['+z_0']))
    return lon, lat, alt
