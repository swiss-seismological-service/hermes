# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Utilities for seismic data import.
"""

import datetime
import io

from lxml import etree
from obspy import read_events

from ramsis.datamodel.seismics import SeismicObservationCatalog, SeismicEvent
from RAMSIS.io.utils import (IOBase, DeserializerBase, SerializerBase,
                             _IOError, TransformationError, )

_QUAKEML_HEADER = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<q:quakeml xmlns="http://quakeml.org/xmlns/bed/1.2" '
    b'xmlns:q="http://quakeml.org/xmlns/quakeml/1.2">'
    b'<eventParameters publicID="smi:scs/0.7/EventParameters">')

_QUAKEML_FOOTER = b'</eventParameters></q:quakeml>'

_QUAKEML_SRS_EPSG = 'epsg:4326'


class QuakeMLCatalogIOError(_IOError):
    """QuakeML de-/serialization error ({})."""


class InvalidMagnitudeType(QuakeMLCatalogIOError):
    """Event with invalid magnitude type {!r} detected."""


class QuakeMLCatalogDeserializer(DeserializerBase, IOBase):
    """
    Deserializes `QuakeML <https://quake.ethz.ch/quakeml/>`_ data into an
    RT-RAMSIS seismic catalog.
    """
    NSMAP_QUAKEML = {None: "http://quakeml.org/xmlns/bed/1.2",
                     'q': "http://quakeml.org/xmlns/quakeml/1.2"}
    SRS_EPSG = _QUAKEML_SRS_EPSG

    LOGGER = 'RAMSIS.io.quakemldeserializer'

    def __init__(self, mag_type=None, **kwargs):
        """
        :param mag_type: Describes the type of magnitude events should be
            configured with. If :code:`None` the magnitude type is not
            verified (default).
        :type mag_type: str or None
        :param transform_func: Function reference for transforming data
            into local coordinate system
        """
        super().__init__(**kwargs)

        self._mag_type = mag_type

    def _deserialize(self, data):
        """
        Deserialize `QuakeML <https://quake.ethz.ch/quakeml/>`_ data into an
        RT-RAMSIS seismic catalog.

        :param data: Data to be deserialized.

        :returns: Seismic catalog
        :rtype: :py:class:`ramsis.datamodel.seismics.SeismicObservationCatalog`
        """
        if isinstance(data, str):
            data = data.encode(encoding='utf-8')

        if not isinstance(data, (bytes, bytearray)):
            raise TypeError('The data object must be str, bytes or bytearray, '
                            'not {!r}'.format(data.__class__.__name__))

        return SeismicObservationCatalog(
            creationinfo_creationtime=datetime.datetime.utcnow(),
            events=[e for e in self._get_events(io.BytesIO(data))])

    def _loado(self, data):
        return SeismicObservationCatalog(
            creationinfo_creationtime=datetime.datetime.utcnow(),
            events=[e for e in self._get_events(data, parser=etree.iterwalk)])

    def _deserialize_event(self, event_element, **kwargs):
        """
        Deserialize a single `QuakeML <https://quake.ethz.ch/quakeml/>`_
        event and perform *indexing*.

        :param bytes event_element: `QuakeML <https://quake.ethz.ch/quakeml/>`_
            event element

        :returns: Seismic event
        :rtype: :py:class:`ramsis.datamodel.seismics.Event`
        """
        def create_pseudo_catalog(event_element):
            """
            Creates a QuakeML catalog from a single event.

            :param bytes event_element: `QuakeML
                <https://quake.ethz.ch/quakeml/>`_ event element

            .. note::

                ObsPy does not implement parsing *plain* QuakeML events. As a
                consequence, this workaround is in use i.e. creating a pseudo
                catalog from a single event.
            """
            return io.BytesIO(
                _QUAKEML_HEADER + event_element + _QUAKEML_FOOTER)

        def add_prefix(prefix, d, replace_args=['_', '']):
            if not replace_args:
                replace_args = ["", ""]

            return {"{}{}".format(prefix, k.replace(*replace_args)): v
                    for k, v in d.items()}

        try:
            e = read_events(create_pseudo_catalog(event_element))[0]
        except Exception as err:
            raise QuakeMLCatalogIOError(f'While parsing QuakeML: {err}')
        else:
            self.logger.debug(f"Importing seismic event: {e.short_str()} ...")

        attr_dict = {}
        magnitude = e.preferred_magnitude()
        if self._mag_type and magnitude.magnitude_type != self._mag_type:
            raise InvalidMagnitudeType(magnitude.magnitude_type)

        attr_dict['magnitude_value'] = magnitude.mag
        attr_dict.update(add_prefix('magnitude_', magnitude.mag_errors))

        origin = e.preferred_origin()
        attr_dict['datetime_value'] = origin.time.datetime
        attr_dict.update(add_prefix('datetime_', origin.time_errors))

        x = origin.longitude
        y = origin.latitude
        z = origin.depth

        # convert origin into local CRS
        try:
            x, y, z = self.transform_func(origin.longitude, origin.latitude,
                                          origin.depth)
        except Exception as err:
            raise TransformationError(err)

        attr_dict['x_value'] = x
        attr_dict.update(add_prefix('x_', origin.longitude_errors))
        attr_dict['y_value'] = y
        attr_dict.update(add_prefix('y_', origin.latitude_errors))
        attr_dict['z_value'] = z
        attr_dict.update(add_prefix('z_', origin.depth_errors))

        attr_dict['quakeml'] = event_element

        return SeismicEvent(**attr_dict)

    def _get_events(self, data, parser=etree.iterparse):
        """
        Generator yielding the deserialized events of a seismic catalog.

        :param data: Data events are deserialized from
        """
        parse_kwargs = {'events': ('end',),
                        'tag': "{%s}event" % self.NSMAP_QUAKEML[None]}

        try:
            for event, element in parser(data, **parse_kwargs):
                if event == 'end' and len(element):
                    try:
                        yield self._deserialize_event(etree.tostring(element))
                    except InvalidMagnitudeType:
                        continue

        except etree.XMLSyntaxError as err:
            raise QuakeMLCatalogIOError(err)


class QuakeMLCatalogSerializer(SerializerBase, IOBase):
    """
    Serializes a RT-RAMSIS seismic catalog into `QuakeML
    <https://quake.ethz.ch/quakeml/>`_.
    """

    def _serialize(self, data):
        """
        Serialize a seismic catalog.

        :param data: Seismic catalog
        :type data: :py:class:
            `ramsis.datamodel.seismics.SeismicObservationCatalog`

        :returns: Serialized QuakeML seismic catalog
        :rtype: str
        """
        # XXX(damb): Since before, the QuakeML event snippet was stored
        # without modification transforming corrdinates is not required.
        return (_QUAKEML_HEADER + b''.join(e.quakeml for e in data.events) +
                _QUAKEML_FOOTER).decode('utf-8')


IOBase.register(QuakeMLCatalogDeserializer)
IOBase.register(QuakeMLCatalogSerializer)
DeserializerBase.register(QuakeMLCatalogDeserializer)
SerializerBase.register(QuakeMLCatalogSerializer)
