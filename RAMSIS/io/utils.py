# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
General purpose IO utilities.
"""

import abc
import contextlib
import functools
import io
import logging

from pyproj import Transformer
import requests

from marshmallow import fields, validate

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
        self.external_proj = kwargs.get("external_proj")
        if not self.external_proj:
            self.external_proj = 'epsg:4326'

        for atr in ['ref_easting', 'ref_northing', 'ramsis_proj',
                    'transform_func_name']:
            if kwargs.get(atr) is None:
                raise ValueError(
                    f"IOBase requires {atr} to be passed in kwargs.")
            setattr(self, atr, kwargs.get(atr))

        self.coordinate_transformer = RamsisCoordinateTransformer(
            self.ref_easting, self.ref_northing,
            self.ramsis_proj, self.external_proj)
        self.transform_func = _callable_or_raise(
            getattr(self.coordinate_transformer, self.transform_func_name))

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
        self._transform_callback = _callable_or_raise(
            getattr(self.coordinate_transformer, func))
        return func


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
def append_ms_zeroes(dt_str):
    """
    Utility function zero padding milliseconds.

    :param str dt_str: Date time string to be processed

    :returns: Date time string with padded milliseconds
    :rtype: str
    """
    if '.' in dt_str:
        return dt_str
    return dt_str + '.000000'


@contextlib.contextmanager
def binary_request(request, url, params={}, timeout=None,
                   nocontent_codes=(204,), **kwargs):
    """
    Make a binary request

    :param request: Request object to be used
    :type request: :py:class:`requests.Request`
    :param str url: URL
    :params dict params: Dictionary of query parameters
    :param timeout: Request timeout
    :type timeout: None or int or tuple

    :rtype: io.BytesIO
    """
    try:
        r = request(url, params=params, timeout=timeout, **kwargs)
        if r.status_code in nocontent_codes:
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


class RamsisCoordinateTransformer:
    def __init__(self, ref_easting, ref_northing,
                 ramsis_proj, external_proj=4326):
        self.ref_easting = ref_easting
        self.ref_northing = ref_northing
        self.ramsis_proj = ramsis_proj
        self.external_proj = external_proj

        self.transformer_to_ramsis = Transformer.from_proj(
            self.external_proj, self.ramsis_proj)
        self.transformer_to_external = Transformer.from_proj(
            self.ramsis_proj, self.external_proj)

    def pyproj_transform_to_local_coords(self, lat, lon, depth=None):
        # Easting and northing in projected coordinates
        easting_0, northing_0 = self.transformer_to_ramsis.transform(lat, lon)
        easting = easting_0 - self.ref_easting
        northing = northing_0 - self.ref_northing
        altitude = -depth

        return easting, northing, altitude

    def pyproj_transform_from_local_coords(self, easting, northing, altitude=None):
        easting_0 = easting + self.ref_easting
        northing_0 = northing + self.ref_northing

        lat, lon = self.transformer_to_external.transform(easting_0,
                                                          northing_0)
        depth = -altitude
        return lat, lon, depth
