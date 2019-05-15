# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Utilities for seismic data import.
"""

import datetime
import io

from obspy import read_events

from ramsis.datamodel.seismics import SeismicCatalog, SeismicEvent
from RAMSIS.io.resource import Resource, EResource
from RAMSIS.io.utils import (IOBase, DeserializerBase, _IOError,
                             TransformationError)


class QuakeMLIOError(_IOError):
    """QuakeML de-/serialization error ({})."""


class InvalidMagnitudeType(QuakeMLIOError):
    """Event with invalid magnitude type {!r} detected."""


class QuakeMLDeserializer(DeserializerBase, IOBase):
    """
    Deserializes `QuakeML <https://quake.ethz.ch/quakeml/>`_ data into an
    RT-RAMSIS seismic catalog.
    """
    RESOURCE_TYPE = EResource.QUAKEML

    LOGGER = 'RAMSIS.io.quakemldeserializer'

    def __init__(self, loader, mag_type=None, **kwargs):
        """
        :param loader: Loader instance used for resource loading
        :type loader: :py:class:`RAMSIS.io.utils.ResourceLoader`
        :param str proj: Spatial reference system in Proj4 notation
            representing the local coordinate system
        :param mag_type: Describes the type of magnitude events should be
            configured with. If :code:`None` the magnitude type is not
            verified (default).
        :type mag_type: str or None
        :param transform_callback: Function reference for transforming data
            into local coordinate system
        """
        super().__init__(**kwargs)

        self._proj = kwargs.get('proj')
        if not self._proj:
            raise QuakeMLIOError("Missing SRS (PROJ4) projection.")

        self._mag_type = kwargs.get('mag_type')
        self._resource = Resource.create_resource(self.RESOURCE_TYPE,
                                                  loader=loader)

    @property
    def proj(self):
        return self._proj

    def _deserialize(self):
        """
        Deserialize `QuakeML <https://quake.ethz.ch/quakeml/>`_ data into an
        RT-RAMSIS seismic catalog.

        :returns: Seismic catalog
        :rtype: :py:class:`ramsis.datamodel.seismics.SeismicCatalog`
        """
        return SeismicCatalog(
            creationinfo_creationtime=datetime.datetime.utcnow(),
            events=[e for e in self])

    def _deserialize_event(self, event_element):
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
                self._resource.QUAKEML_HEADER +
                event_element +
                self._resource.QUAKEML_FOOTER)

        def add_prefix(prefix, d, replace_args=['_', '']):
            if not replace_args:
                replace_args = ["", ""]

            return {"{}{}".format(prefix, k.replace(*replace_args)): v
                    for k, v in d.items()}

        try:
            e = read_events(create_pseudo_catalog(event_element))[0]
        except Exception as err:
            raise QuakeMLIOError(f'While parsing QuakeML: {err}')
        else:
            self.logger.debug(f"Importing seismic event: {e} ...")

        attr_dict = {}
        magnitude = e.preferred_magnitude()
        if self._mag_type and magnitude.magnitude_type != self._mag_type:
            raise InvalidMagnitudeType(magnitude.magnitude_type)

        attr_dict['magnitude_value'] = magnitude.mag
        attr_dict.update(add_prefix('magnitude_', magnitude.mag_errors))

        origin = e.preferred_origin()
        attr_dict['datetime_value'] = origin.time.datetime
        attr_dict.update(add_prefix('datetime_', origin.time_errors))

        crs_transform = self._transform_callback or self._transform
        # convert origin into local CRS
        try:
            x, y, z = crs_transform(origin.longitude, origin.latitude,
                                    origin.depth, self._resource.SRS_ESPG,
                                    self.proj)
        except Exception as err:
            raise TransformationError(err)

        attr_dict['x_value'] = x
        attr_dict.update(add_prefix('x_', origin.longitude_errors))
        attr_dict['y_value'] = y
        attr_dict.update(add_prefix('y_', origin.latitude_errors))
        attr_dict['z_value'] = z
        attr_dict.update(add_prefix('z_', origin.depth_errors))

        return SeismicEvent(**attr_dict)

    def __iter__(self):
        """
        Generator yielding the deserialized events of a seismic catalog.
        """
        for qml_event in self._resource:
            try:
                yield self._deserialize_event(qml_event)
            except InvalidMagnitudeType:
                continue


IOBase.register(QuakeMLDeserializer)
DeserializerBase.register(QuakeMLDeserializer)
