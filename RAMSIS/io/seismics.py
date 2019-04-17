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
from RAMSIS.io.utils import IOBase, _IOError, _callable_or_raise


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
        """
        super().__init__()

        self._proj = kwargs.get('proj')
        if not self._proj:
            raise QuakeMLError("Missing SRS (PROJ4) projection.")

        self._transform_callback = _callable_or_raise(
            kwargs.get('transform_callback'))
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
            raise QuakeMLError(f'While parsing QuakeML: {err}')
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
                                    origin.depth, self.proj)
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
            except InvalidMagnitudeType as err:
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
        self._transform_callback = func
        return func

    load = _deserialize


IOBase.register(QuakeMLDeserializer)
