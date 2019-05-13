# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Resource utilites

Resource implementations define the data sources.
"""

import abc
import enum

from lxml import etree

from RAMSIS.io.utils import RequestsError

from ramsis.utils.error import Error


class EResource(enum.Enum):
    QUAKEML = enum.auto()
    JSON = enum.auto()


class ResourceError(Error):
    """Base resource error ({})."""


class ResourceBase(abc.ABC):
    """
    Resource base class

    Concrete implementations of :py:class:`Resource` implement both incremental
    loading and loading in a single step.
    """

    def __init__(self, loader, **kwargs):
        """
        :param loader: Resource loader instance returning a file-like object
        :type loader: :py:class:`RAMSIS.io.utils.ResourceLoader`
        """
        self._loader = loader

    def load(self):
        """
        Load a resource.

        :returns: Loaded resource
        :rtype: bytes
        """
        try:
            return self._loader().read()
        except Error as err:
            raise ResourceError(err)

    @staticmethod
    def create_resource(resource_format, **kwargs):

        if resource_format == EResource.QUAKEML:
            return QuakeMLResource(**kwargs)
        elif resource_format == EResource.JSON:
            return JSONResource(**kwargs)

        raise ResourceError('Unknown resource type.')

    @abc.abstractmethod
    def __iter__(self):
        """
        Generator allowing iteration over the resource formats' events.
        """
        while False:
            yield None


Resource = ResourceBase


class QuakeMLResource(ResourceBase):
    """
    Concrete implementation of :py:class:`Resource` providing `QUAKEML
    <https://quake.ethz.ch/quakeml/>`  data.

    .. note:: Currently, only HTTP GET requests are supported.
    """

    RESOURCE_TYPE = EResource.QUAKEML.name
    NSMAP_QUAKEML = {None: "http://quakeml.org/xmlns/bed/1.2",
                     'q': "http://quakeml.org/xmlns/quakeml/1.2"}
    # TODO(damb): Move to general purpose settings?
    QUAKEML_HEADER = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<q:quakeml xmlns="http://quakeml.org/xmlns/bed/1.2" '
        b'xmlns:q="http://quakeml.org/xmlns/quakeml/1.2">'
        b'<eventParameters publicID="smi:scs/0.7/EventParameters">')

    QUAKEML_FOOTER = b'</eventParameters></q:quakeml>'
    QUAKEML_SRS_ESPG = 4326

    def __iter__(self):
        """
        Fetch a `QUAKEML <https://quake.ethz.ch/quakeml/>`_ catalog
        incrementally.
        """
        parse_kwargs = {'events': ('end',),
                        'tag': "{%s}event" % self.NSMAP_QUAKEML[None]}
        try:
            for event, element in etree.iterparse(self._loader(),
                                                  **parse_kwargs):

                if event == 'end' and len(element):
                    yield etree.tostring(element)

        except (RequestsError, etree.XMLSyntaxError) as err:
            raise ResourceError(err)


class JSONResource(ResourceBase):
    """
    Dummy implementation of :py:class:`Resource` providing JSON data.
    """
    RESOURCE_TYPE = EResource.JSON.name

    def __iter__(self):
        # TODO(damb): Might provide iteration over the child elements using
        # ijson.
        raise NotImplementedError


ResourceBase.register(QuakeMLResource)
ResourceBase.register(JSONResource)
