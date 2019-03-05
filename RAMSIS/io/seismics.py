# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Utitlities for seismic data import.
"""

import datetime
import io

from obspy import read_events
from osgeo import ogr, osr

from ramsis.datamodel.seismics import SeismicCatalog, SeismicEvent
from RAMSIS.io.resource import Resource, EResource
from RAMSIS.io.utils import IOBase, _IOError


class QuakeMLError(_IOError):
    """QuakeML de-/serialization error ({})."""


class InvalidMagnitudeType(QuakeMLError):
    """Event with invalid magnitude type {!r} detected."""


class TransformationError(QuakeMLError):
    """Error while performing CRS transformation: {}"""


class QuakeMLDeserializer(IOBase):
    """
    Deserializes `QuakeML <https://quake.ethz.ch/quakeml/>`_ data into an
    RT-RAMSIS seismic catalog.
    """
    RESOURCE_TYPE = EResource.QuakeML

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
        """
        super().__init__(logger=self.LOGGER)
        try:
            self._proj = kwargs['proj']
        except KeyError as err:
            raise QuakeMLError(f"Missing SRS projection: {err}")

        self._mag_type = kwargs['mag_type']
        self._resource = Resource.create_resource(self.RESOURCE_TYPE,
                                                  loader=loader)

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

                ObsPy does not implement parsing QuakeML events *only*. As a
                consequence, creating a pseudo catalog with a single event is
                necessary.
            """
            return io.BytesIO(
                self.QUAKEML_HEADER + event_element + self.QUAKEML_FOOTER)

        def add_prefix(prefix, d):
            return {f"{prefix}{k}": v for k, v in d.items()}

        try:
            e = read_events(create_pseudo_catalog(event_element))[0]
        except Exception as err:
            raise QuakeMLError(f'While parsing QuakeML: {err}')
        else:
            self.logger.debug(f"Importing seismic event: {e} ...")

        attr_dict = {}
        magnitude = e.preferred_magnitude
        if self._mag_type and magnitude.magnitude_type != self._mag_type:
            raise InvalidMagnitudeType(magnitude.magnitude_type)

        attr_dict['magnitude'] = magnitude.mag
        attr_dict.update(add_prefix('magnitude_', magnitude.mag_errors))

        origin = e.preferred_origin
        attr_dict['datetime_value'] = origin.time.datetime
        attr_dict.update(add_prefix('datetime_', origin.time_errors))

        # convert origin into local CRS
        try:
            x, y, z = self._transform(origin.longitude, origin.latitude,
                                      origin.depth, self._proj)
        except Exception as err:
            raise TransformationError(err)

        attr_dict['x'] = x
        attr_dict.update(add_prefix('x_', origin.longitude_errors))
        attr_dict['y'] = y
        attr_dict.update(add_prefix('y_', origin.latitude_errors))
        attr_dict['z'] = z
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

    def _transform(self, x, y, z, proj):
        """
        Utility method performing a spatial transformation

        :param float x: X value
        :param float y: Y value
        :param float z: Z value
        :param str proj: Target CRS description (PROJ4)

        :returns: Transformed values
        :rtype: tuple
        """
        source_srs = osr.SpatialReference()
        source_srs.ImportFromEPSG(self._resource.QUAKEML_SRS_ESPG)

        target_srs = osr.SpatialReference()
        target_srs.ImportFromProj4(proj)

        t = osr.CoordinateTransformation(source_srs, target_srs)
        # convert to WKT
        point_z = ogr.CreateGeometryFromWkt(f"POINT_Z ({x} {y} {z})")
        point_z.Transform(t)

        return point_z.GetX(), point_z.GetY(), point_z.GetZ()

    load = _deserialize


IOBase.register(QuakeMLDeserializer)
