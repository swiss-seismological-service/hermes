# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Utilities for SFM-Worker data import/export.
"""

import base64
import functools

from marshmallow import Schema, fields, pre_dump, post_dump, ValidationError
from osgeo import ogr, gdal

from RAMSIS.io.seismics import QuakeMLCatalogSerializer
from RAMSIS.io.hydraulics import HYDWSBoreholeHydraulicsSerializer
from RAMSIS.io.utils import SerializerBase, IOBase, _IOError

gdal.UseExceptions()


class SFMWIOError(_IOError):
    """Base SFMW de-/serialization error ({})."""

# TODO(damb): Implement a solution based on hydraulics


class _SchemaBase(Schema):
    """
    Schema base class.
    """
    @classmethod
    def _clear_missing(cls, data):
        retval = data.copy()
        for key in filter(lambda key: data[key] in (None, {}, []), data):
            del retval[key]
        return retval


class _SeismicCatalogSchema(_SchemaBase):
    """
    Schema representation of a seismic catalog.
    """
    # XXX(damb): Use a string in favor of bytes since bytes cannot be
    # serialized into JSON
    quakeml = fields.String(required=True)

    @pre_dump
    def make_catalog(self, data, **kwargs):
        """
        Convert an instance of
        :py:class:`ramsis.datamodel.seismics.SeismicCatalog` into its `QuakeML
        <https://quake.ethz.ch/quakeml/>`_ representation.
        """
        if 'quakeml' in data:
            data['quakeml'] = QuakeMLCatalogSerializer().dumps(data['quakeml'])

        return data

    @post_dump
    def b64encode(self, data, **kwargs):
        """
        Encode the catalog using base64 encoding.
        """
        if 'quakeml' in data:
            data['quakeml'] = base64.b64encode(
                data['quakeml'].encode('utf8')).decode('utf8')

        return data


class _ReservoirSchema(_SchemaBase):
    """
    Schema representation of a reservoir to be forecasted.
    """
    ALLOWED_GEOMS = ('POLYHEDRALSURFACE')

    # XXX(damb): WKT/WKB
    geom = fields.String()

    # TODO(damb): Attributes to be verified.
    event_rate = fields.Float()
    b_value = fields.Float()
    std_event_rate = fields.Float()

    # XXX(damb): Currently no sub_geometries are supported.
    # sub_geometries = fields.Nested('self', many=True)

    @post_dump
    def transform(self, data, **kwargs):
        if (not self.context.get('proj') or
            'transform_callback' not in self.context or
                'geom' not in data):
            return data

        try:
            geom = ogr.CreateGeometryFromWkt(data['geom'])
        except Exception as err:
            raise ValidationError(f"Invalid geometry ({err}).")

        if geom.GetGeometryName() not in self.ALLOWED_GEOMS:
            raise ValidationError(
                f"Unknown geometry type {geom.GetGeometryName()!r}")

        transform_func = self.context['transform_callback']
        try:
            phsf = ogr.Geometry(ogr.wkbPolyhedralSurfaceZ)
            for i in range(0, geom.GetGeometryCount()):
                g = geom.GetGeometryRef(i)
                ring = ogr.Geometry(ogr.wkbLinearRing)
                for j in range(0, g.GetGeometryRef(0).GetPointCount()):
                    ring.AddPoint(
                        *transform_func(*g.GetGeometryRef(0).GetPoint(j)))
                polygon = ogr.Geometry(ogr.wkbPolygon)
                polygon.AddGeometry(ring)
                phsf.AddGeometry(polygon)

            data['geom'] = phsf.ExportToWkt()
        except Exception as err:
            raise ValidationError(
                f"Error while transforming coordinates: {err}")

        return data


class _ScenarioSchema(_SchemaBase):
    """
    Schema representation for a scenario to be forecasted.
    """
    # XXX(damb): Borehole scenario for both the related geometry and the
    # injection plan.
    well = fields.Dict(keys=fields.Str())

    @pre_dump
    def serialize_well(self, data, **kwargs):
        if 'well' in data:
            serializer = HYDWSBoreholeHydraulicsSerializer(
                plan=True,
                proj=self.context.get('proj'),
                transform_callback=self.context.get('transform_callback'))

            # XXX(damb): This is not a nice solution. Something like
            # marshmallow's dump method would be required to avoid dumping to a
            # string firstly just to load the data afterwards, again.
            data['well'] = serializer._dumpo(data['well'])

        return data


class _SFMWorkerIMessageSchema(_SchemaBase):
    """
    Schema implementation for serializing input messages for seismicity
    forecast model worker implementations.

    .. note::

        With the current protocol version only a single well is supported.
    """
    seismic_catalog = fields.Nested(_SeismicCatalogSchema)
    # XXX(damb): Implicit definition of an injection well in order to allow
    # serialization by means of the appropriate RT-RAMSIS borehole serializer.
    # Note, that a well comes along with its hydraulics.
    well = fields.Dict(keys=fields.Str())
    scenario = fields.Nested(_ScenarioSchema)
    reservoir = fields.Nested(_ReservoirSchema)
    # XXX(damb): model_parameters are optional
    model_parameters = fields.Dict(keys=fields.Str())

    @pre_dump
    def serialize_well(self, data, **kwargs):
        if 'well' in data:
            serializer = HYDWSBoreholeHydraulicsSerializer(
                plan=False,
                proj=self.context.get('proj'),
                transform_callback=self.context.get('transform_callback'))

            # XXX(damb): This is not a nice solution. Something like
            # marshmallow's dump method would be required to avoid dumping to a
            # string firstly just to load the data afterwards, again.
            data['well'] = serializer._dumpo(data['well'])

        return data

    @post_dump
    def skip_missing(self, data, **kwargs):
        return self._clear_missing(data)


class SFMWorkerIMessageSerializer(SerializerBase, IOBase):
    """
    Serializes a data structure which later can be consumed by SFM-Workers.
    """

    SRS_EPSG = 4326

    def __init__(self, proj=None, **kwargs):
        """
        :param proj: Spatial reference system in Proj4 notation
            representing the local coordinate system
        :type proj: str or None
        :param transform_callback: Function reference for transforming data
            into local coordinate system
        """
        super().__init__(proj=proj, **kwargs)

    @property
    def _ctx(self):
        crs_transform = self._transform_callback or self._transform

        return {
            'proj': self._proj,
            'transform_callback': functools.partial(
                crs_transform, source_proj=self._proj,
                target_proj=self.SRS_EPSG)}

    def _serialize(self, data):
        """
        Serializes a SFM-Worker payload from the ORM into JSON.
        """
        return _SFMWorkerIMessageSchema(context=self._ctx).dumps(data)

    def _dumpo(self, data):
        return _SFMWorkerIMessageSchema(context=self._ctx).dump(data)


IOBase.register(SFMWorkerIMessageSerializer)
SerializerBase.register(SFMWorkerIMessageSerializer)
