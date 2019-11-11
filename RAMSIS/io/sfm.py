# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Utilities for SFM-Worker data import/export.
"""

import base64
import functools

from geoalchemy2 import WKBElement
from marshmallow import (Schema, fields, pre_dump, post_dump, pre_load,
                         post_load, ValidationError, EXCLUDE)
from osgeo import ogr, gdal

from ramsis.datamodel.seismicity import (ReservoirSeismicityPrediction,
                                         SeismicityPredictionBin)
from RAMSIS.io.seismics import QuakeMLCatalogSerializer
from RAMSIS.io.hydraulics import HYDWSBoreholeHydraulicsSerializer
from RAMSIS.io.utils import (SerializerBase, DeserializerBase, IOBase,
                             _IOError, TransformationError, DateTime,
                             Percentage, Uncertainty, append_ms_zeroes)
from RAMSIS.wkt_utils import wkb_to_wkt

gdal.UseExceptions()


class SFMWIOError(_IOError):
    """Base SFMW de-/serialization error ({})."""


class _SchemaBase(Schema):
    """
    Schema base class.
    """
    class Meta:
        ordered = True

    @classmethod
    def _clear_missing(cls, data):
        retval = data.copy()
        for key in filter(lambda key: data[key] in (None, {}, []), data):
            del retval[key]
        return retval

    @classmethod
    def _flatten_dict(cls, data, sep='_'):
        """
        Flatten a a nested dict :code:`dict` using :code:`sep` as key
        separator.
        """
        retval = {}
        for k, v in data.items():
            if isinstance(v, dict):
                for sub_k, sub_v in cls._flatten_dict(v, sep).items():
                    retval[k + sep + sub_k] = sub_v
            else:
                retval[k] = v

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


class _ModelResultSampleSchema(_SchemaBase):
    """
    Schema representation for a model result sample.
    """
    starttime = DateTime(required=True)
    endtime = DateTime(required=True)

    numberevents_value = fields.Float(required=True)
    numberevents_uncertainty = Uncertainty()
    numberevents_loweruncertainty = Uncertainty()
    numberevents_upperuncertainty = Uncertainty()
    numberevents_confidencelevel = Percentage()

    b_value = fields.Float(required=True)
    b_uncertainy = Uncertainty()
    b_loweruncertainty = Uncertainty()
    b_upperuncertainty = Uncertainty()
    b_confidencelevel = Percentage()

    a_value = fields.Float(required=True)
    a_uncertainy = Uncertainty()
    a_loweruncertainty = Uncertainty()
    a_upperuncertainty = Uncertainty()
    a_confidencelevel = Percentage()

    mc_value = fields.Float(required=True)
    mc_uncertainy = Uncertainty()
    mc_loweruncertainty = Uncertainty()
    mc_upperuncertainty = Uncertainty()
    mc_confidencelevel = Percentage()

    hydraulicvol_value = fields.Float(required=True)
    hydraulicvol_uncertainy = Uncertainty()
    hydraulicvol_loweruncertainty = Uncertainty()
    hydraulicvol_upperuncertainty = Uncertainty()
    hydraulicvol_confidencelevel = Percentage()

    @pre_load
    def append_zero_milliseconds(self, data, **kwargs):
        # XXX(damb): This is a workaround since the DateTime format is being
        # configured with a date string. Is there a better solution provided by
        # marshmallow.
        if 'starttime' in data:
            data['starttime'] = append_ms_zeroes(data['starttime'])

        if 'endtime' in data:
            data['endtime'] = append_ms_zeroes(data['endtime'])

        return data

    @pre_load
    def flatten(self, data, **kwargs):
        return self._flatten_dict(data)

    @post_load
    def make_object(self, data, **kwargs):
        if (self.context.get('format') == 'dict'):
            return data
        return SeismicityPredictionBin(**data)


class _ReservoirSchema(_SchemaBase):
    """
    Schema representation of a reservoir to be forecasted.
    """
    ALLOWED_GEOMS = ('POLYHEDRALSURFACE')

    # XXX(damb): WKT/WKB
    geom = fields.String()
    samples = fields.Nested(_ModelResultSampleSchema, many=True)

    # XXX(damb): Currently no sub_geometries are supported.
    # sub_geometries = fields.Nested('self', many=True)

    @pre_dump
    def wkb_to_wkt(self, data, **kwargs):
        if 'geom' in data and isinstance(data['geom'], WKBElement):
            data['geom'] = wkb_to_wkt(data['geom'])
        return data

    @post_dump
    def transform(self, data, **kwargs):
        if (not self.context.get('proj') or
            'transform_callback' not in self.context or
                'geom' not in data):
            return data

        data['geom'] = self._transform_wkt(data['geom'])

        return data

    @post_load
    def load_postprocess(self, data, **kwargs):
        if (self.context.get('proj') and
                'transform_callback' in self.context):
            data['geom'] = self._transform_wkt(data['geom'])

        if (self.context.get('format') == 'dict'):
            return data
        return ReservoirSeismicityPrediction(**data)

    def _transform_wkt(self, geom):
        try:
            geom = ogr.CreateGeometryFromWkt(geom)
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

            return phsf.ExportToWkt()
        except Exception as err:
            raise TransformationError(f"{err}")

    class Meta:
        unknown = EXCLUDE


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


class _SFMWorkerRunsAttributesSchema(_SchemaBase):
    """
    Schema implementation for serializing attributes for seismicity
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


class _SFMWorkerRunsSchema(_SchemaBase):
    type = fields.Str(default='runs')
    attributes = fields.Nested(_SFMWorkerRunsAttributesSchema)


class _SFMWorkerIMessageSchema(_SchemaBase):
    """
    Schema implementation for serializing input messages for seismicity
    forecast model worker implementations.
    """
    data = fields.Nested(_SFMWorkerRunsSchema)


class SFMWorkerResponseDataAttributesSchema(_SchemaBase):
    """
    Schema representation of the SFM worker response data attributes.
    """
    status = fields.Str()
    status_code = fields.Int()
    forecast = fields.Nested(_ReservoirSchema)
    warning = fields.Str(missing='')

    @post_dump
    def clear_missing(self, data, **kwargs):
        return self._clear_missing(data)


class SFMWorkerResponseDataSchema(_SchemaBase):
    """
    Schema representation fo the SFM worker response data.
    """
    id = fields.UUID()
    attributes = fields.Nested(SFMWorkerResponseDataAttributesSchema)

    @post_dump
    def clear_missing(self, data, **kwargs):
        return self._clear_missing(data)


class _SFMWorkerOMessageSchema(_SchemaBase):
    data = fields.Method("_serialize_data", deserialize="_deserialize_data")

    @post_dump
    def clear_missing(self, data, **kwargs):
        return self._clear_missing(data)

    def _serialize_data(self, obj):
        if 'data' in obj:
            if isinstance(obj['data'], list):
                return SFMWorkerResponseDataSchema(
                    context=self.context, many=True).dump(obj['data'])

            return SFMWorkerResponseDataSchema(
                context=self.context).dump(obj['data'])

    def _deserialize_data(self, value):
        if isinstance(value, list):
            return SFMWorkerResponseDataSchema(
                context=self.context, many=True).load(value)

        return SFMWorkerResponseDataSchema(context=self.context).load(value)


class SFMWorkerIMessageSerializer(SerializerBase, IOBase):
    """
    Serializes a data structure which later can be consumed by SFM-Workers.
    """

    SRS_EPSG = 4326

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


class SFMWorkerOMessageDeserializer(DeserializerBase, IOBase):
    """
    Serializes a data structure which later can be consumed by SFM workers.
    """

    SRS_EPSG = 4326

    def __init__(self, proj=None, **kwargs):
        """
        :param bool many: Allow the deserialization of many arguments
        """
        super().__init__(proj=proj, **kwargs)

        self._context = kwargs.get('context', {'format': 'orm'})
        self._many = kwargs.get('many', False)
        self._partial = kwargs.get('partial', False)

    @property
    def _ctx(self):
        crs_transform = self._transform_callback or self._transform

        self._context.update({
            'proj': self._proj,
            'transform_callback': functools.partial(
                crs_transform, source_proj=self.SRS_EPSG,
                target_proj=self._proj)})

        return self._context

    def _deserialize(self, data):
        """
        Deserializes a data structure returned by SFM-Worker implementations.
        """
        return _SFMWorkerOMessageSchema(
            context=self._ctx, many=self._many).loads(data)

    def _loado(self, data):
        return _SFMWorkerOMessageSchema(
            context=self._ctx, many=self._many,
            partial=self._partial).load(data)


IOBase.register(SFMWorkerIMessageSerializer)
SerializerBase.register(SFMWorkerIMessageSerializer)
IOBase.register(SFMWorkerOMessageDeserializer)
DeserializerBase.register(SFMWorkerOMessageDeserializer)
