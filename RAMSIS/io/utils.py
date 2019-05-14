# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
General purpose IO utilities.
"""

import abc
import io
import logging

import pymap3d
import requests

from urllib.parse import urlparse, urlunparse

from ramsis.utils.error import Error


# NOTE(damb): RequestError instances carry the response, too.
class RequestsError(requests.exceptions.RequestException, Error):
    """Base request error ({})."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class _IOError(Error):
    """Base IO error ({})."""


class InvalidProj4(_IOError):
    """Invalid Proj4 projection specified: {}"""


class TransformationError(_IOError):
    """Error while performing CRS transformation: {}"""


# -----------------------------------------------------------------------------
class IOBase(abc.ABC):
    """
    Abstract IO base class
    """
    LOGGER = 'ramsis.io.io'

    def __init__(self, **kwargs):
        self.logger = logging.getLogger(self.LOGGER)

        self._transform_callback = _callable_or_raise(
            kwargs.get('transform_callback', self._transform))

    def _transform(self, x, y, z, proj):
        """
        Template method implementing the default transformation rule (i.e. no
        transformation).
        """
        return x, y, z

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

            deserializer = QuakeMLDeserializer(loader, proj=proj)

            @deserializer.transform_callback
            def crs_transform(x, y, z, proj):
                return pymap3d_transform(x, y, z, proj)

            cat = deserializer.load()
        """
        self._transform_callback = _callable_or_raise(func)
        return func


class SerializerBase(abc.ABC):
    """
    Abstract base class for serializers.
    """

    @abc.abstractmethod
    def _serialize(self):
        pass

    def dump(self):
        """
        Alias for :py:meth:`_serialize`.
        """
        return self._serialize()


class DeserializerBase(abc.ABC):
    """
    Abstract base class for deserializers.
    """

    @abc.abstractmethod
    def _deserialize(self):
        pass

    def load(self):
        """
        Alias for :py:meth:`_deserialize`.
        """
        return self._deserialize()


# -----------------------------------------------------------------------------
class ResourceLoader(abc.ABC):
    """
    Abstract resource loader base class. Resource loaders build an abstraction
    layer to pretend file-like objects.
    """

    @abc.abstractmethod
    def _load(self):
        """
        :returns: File-like objects
        """
        return io.BytesIO()

    def __call__(self):
        return self._load()


class FileLikeResourceLoader(ResourceLoader):
    """
    General purpose resource loader adapting the interface of any file-like
    object.
    """

    def __init__(self, file_like_obj):
        """
        :param file_like_obj: File-like object to be wrapped
        """
        self._file_like = file_like_obj

    def _load(self):
        return self._file_like


class HTTPGETResourceLoader(ResourceLoader):
    """
    Resource loader implementing loading data from an URL using the HTTP
    **GET** request method.
    """

    def __init__(self, url, params={}, timeout=None):
        self._url, self._params = self.validate_ctor_args(url, params)
        self._timeout = timeout

    def _load(self):
        try:
            r = requests.get(self._url,
                             params=self._params,
                             timeout=self._timeout)

        except RequestsError as err:
            # XXX(damb): Make sure that an instance of ramsis.utils.error.Error
            # can be caught
            raise err

        return io.BytesIO(r.content)

    @staticmethod
    def validate_ctor_args(url, params):
        _url = urlparse(url)

        if _url.params or _url.query or _url.fragment:
            raise ValueError(f"Invalid URL: {url}")

        return urlunparse(_url), params


class HTTPGETStreamResourceLoader(HTTPGETResourceLoader):
    """
    Resource loader implementing streamed loading from an URL using the HTTP
    **GET** request method.
    """

    def _load(self):
        try:
            r = requests.get(self._url,
                             params=self._params,
                             timeout=self._timeout,
                             stream=True)
            r.raw.decode_content = True
        except RequestsError as err:
            # XXX(damb): Make sure that an instance of ramsis.utils.error.Error
            # can be caught
            raise err

        return r.raw


ResourceLoader.register(FileLikeResourceLoader)
ResourceLoader.register(HTTPGETResourceLoader)
ResourceLoader.register(HTTPGETStreamResourceLoader)


def _callable_or_raise(obj):
    """
    Makes sure an object is callable if it is not :code:`None`.

    :returns: Object validated
    :raises: ValueError: If :code:`obj` is not callable
    """
    if obj and not callable(obj):
        raise ValueError(f"{obj!r} is not callable.")
    return obj


def pymap3d_transform(x, y, z, proj):
    """
    Utility method performing a spatial transformation relying on `pymap3d
    <https://github.com/scivision/pymap3d>`.

    :param float x: X value
    :param float y: Y value
    :param float z: Z value
    :param str proj: Target CRS description (PROJ4)

    :returns: Transformed values
    :rtype: tuple
    """
    # extract observer position from proj4 string
    origin = dict([v.split('=') for v in proj.split(' ')
                   if (v.startswith('+x_0') or
                       v.startswith('+y_0') or
                       v.startswith('+z_0'))])

    if len(origin) != 3:
        raise ValueError(f"Invalid proj4 string: {proj!r}")

    return pymap3d.geodetic2ned(
        x, y, z, int(origin['+y_0']), int(origin['+x_0']), int(origin['+z_0']))
