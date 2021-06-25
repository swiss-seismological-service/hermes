# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Utilities for SFM-Worker data import/export.
"""

import base64
from marshmallow import (Schema, fields, pre_dump, post_dump, pre_load,
                         post_load, EXCLUDE)
from osgeo import gdal

from ramsis.datamodel.seismicity import (ReservoirSeismicityPrediction,
                                         SeismicityPredictionBin)
from RAMSIS.io.seismics import QuakeMLCatalogSerializer
from RAMSIS.io.hydraulics import HYDWSBoreholeHydraulicsSerializer
from RAMSIS.io.utils import (SerializerBase, DeserializerBase, IOBase,
                             _IOError, DateTime, TransformationError,
                             Percentage, Uncertainty, append_ms_zeroes)

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
        :py:class:`ramsis.datamodel.seismics.SeismicObservationCatalog` into its `QuakeML
        <https://quake.ethz.ch/quakeml/>`_ representation.
        """
        if 'quakeml' in data:
            data['quakeml'] = QuakeMLCatalogSerializer(
                transform_func_name=self.context.get('transform_func_name'),
                ramsis_proj=self.context.get('ramsis_proj'),
                external_proj=self.context.get('external_proj'),
                ref_easting=self.context.get('ref_easting'),
                ref_northing=self.context.get('ref_northing')).\
                dumps(data['quakeml'])

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

    hydraulicvol_value = fields.Float()
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
    x = fields.List(fields.Float(), required=True)
    y = fields.List(fields.Float(), required=True)
    z = fields.List(fields.Float(), required=True)

    @pre_load
    def validate_geom(self, data, **kwargs):
        assert set(['x', 'y', 'z']) <= set(data.keys())
        for dim in ['x', 'y', 'z']:
            val_list = data[dim]
            assert isinstance(val_list, list), ("Dimensional list length "
                                                "must equal or exceed 2")
            # Check that the values in each list are strictly increasing
            # Same numbers are not allowed as that would create zero-width
            # subgeometries.
            assert all(x < y for x, y in zip(val_list, val_list[1:]))
            assert len(val_list) >= 2
        return data


class _GeomSchema(_SchemaBase):
    geom = fields.Nested(_ReservoirSchema)


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
                transform_func_name=self.context.get('transform_func_name'),
                ramsis_proj=self.context.get('ramsis_proj'),
                external_proj=self.context.get('external_proj'),
                ref_easting=self.context.get('ref_easting'),
                ref_northing=self.context.get('ref_northing'))

            # XXX(damb): This is not a nice solution. Something like
            # marshmallow's dump method would be required to avoid dumping to a
            # string firstly just to load the data afterwards, again.
            data['well'] = serializer._dumpo(data['well'])

        return data


class _ReferencePointSchema(_SchemaBase):
    """
    Schema representation of a reservoir to be forecasted.
    """
    x = fields.Float(required=True)
    y = fields.Float(required=True)


class _SFMWorkerRunsAttributesSchema(_SchemaBase):
    """
    Schema implementation for serializing attributes for seismicity
    forecast model worker implementations.

    .. note::

        With the current protocol version only a single well is supported.
    """
    reservoir = fields.Nested(_GeomSchema)
    spatialreference = fields.Str()
    referencepoint = fields.Nested(_ReferencePointSchema)
    seismic_catalog = fields.Nested(_SeismicCatalogSchema)
    # XXX(damb): Implicit definition of an injection well in order to allow
    # serialization by means of the appropriate RT-RAMSIS borehole serializer.
    # Note, that a well comes along with its hydraulics.
    well = fields.Dict(keys=fields.Str())
    scenario = fields.Nested(_ScenarioSchema)
    # XXX(damb): model_parameters are optional
    model_parameters = fields.Dict(keys=fields.Str())

    @pre_dump
    def serialize_well(self, data, **kwargs):
        if 'well' in data:
            serializer = HYDWSBoreholeHydraulicsSerializer(
                plan=False,
                transform_func_name=self.context.get('transform_func_name'),
                ramsis_proj=self.context.get('ramsis_proj'),
                external_proj=self.context.get('external_proj'),
                ref_easting=self.context.get('ref_easting'),
                ref_northing=self.context.get('ref_northing'))

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


class _SeismicityForecastGeomSchema(_SchemaBase):
    """
    Schema representation of seismicity forecast samples.
    """
    x_min = fields.Float()
    x_max = fields.Float()
    y_min = fields.Float()
    y_max = fields.Float()
    z_min = fields.Float()
    z_max = fields.Float()

    @pre_load
    def flatten(self, data, **kwargs):
        return self._flatten_dict(data)

    @pre_dump
    def transform_dump(self, data, **kwargs):
        """
        Transform coordinates from local to external coordinates.
        """
        transform_func = self.context['transform_func']
        print("before transformation: ", data.x_min, data.x_max)
        print("transform func", transform_func)
        try:
            (data.x_min,
             data.y_min,
             _) = transform_func(
                data.x_min,
                data.y_min)
            (data.x_max,
             data.y_max,
             _) = transform_func(
                data.x_max,
                data.y_max)
            print("after transformation: ", data.x_min, data.x_max)

        except (TypeError, ValueError, AttributeError) as err:
            raise TransformationError(f"{err}")

        return data

    @post_dump
    def add_geom(self, data, **kwargs):
        """
        Add linear ring made from bounding box values.
        This is required by Openquake.
        """
        linearring = (
            f"{data['x_min']} {data['y_min']} "
            f"{data['x_max']} {data['y_min']} "
            f"{data['x_max']} {data['y_max']} "
            f"{data['x_min']} {data['y_max']} ")
        return {'linearring': linearring}

    class Meta:
        unknown = EXCLUDE


class _SeismicityForecastSamplesSchema(_SeismicityForecastGeomSchema):
    """
    Schema representation of seismicity forecast samples.
    """
    samples = fields.Nested(_ModelResultSampleSchema, many=True)
    subgeometries = fields.Nested('self', exclude=('subgeometries',),
                                  many=True)

    @post_load
    def post_load_data(self, data, **kwargs):
        for d_min, d_max in [
                ('x_min', 'x_max'),
                ('y_min', 'y_max'),
                ('z_min', 'z_max')]:
            if data[d_min] and data[d_max]:
                assert data[d_min] < data[d_max]
        if (self.context.get('format') == 'dict'):
            return data
        return ReservoirSeismicityPrediction(**data)

    class Meta:
        unknown = EXCLUDE


class SFMWorkerResponseDataAttributesSchema(_SchemaBase):
    """
    Schema representation of the SFM worker response data attributes.
    """
    status = fields.Str()
    status_code = fields.Int()
    forecast = fields.Nested(_SeismicityForecastSamplesSchema)
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

    SRS_EPSG = "epsg:4326"

    @property
    def _ctx(self):
        return {
            'transform_func_name': self.transform_func_name,
            'ramsis_proj': self.ramsis_proj,
            'external_proj': self.external_proj,
            'ref_easting': self.ref_easting,
            'ref_northing': self.ref_northing}

    def _serialize(self, data):
        """
        Serializes a SFM-Worker payload from the ORM into JSON.
        """
        return _SFMWorkerIMessageSchema(context=self._ctx).dumps(data)

    def _serialize_dict(self, data):
        return _SFMWorkerIMessageSchema(context=self._ctx).dump(data)


class SFMWorkerOMessageDeserializer(DeserializerBase, IOBase):
    """
    Serializes a data structure which later can be consumed by SFM workers.
    """

    SRS_EPSG = "epsg:4326"

    def __init__(self, **kwargs):
        """
        :param bool many: Allow the deserialization of many arguments
        """
        super().__init__(**kwargs)

        self._context = kwargs.get('context', {'format': 'orm'})
        self._many = kwargs.get('many', False)
        self._partial = kwargs.get('partial', False)

    @property
    def _ctx(self):
        self._context.update({
            'transform_func_name': self.transform_func_name,
            'ramsis_proj': self.ramsis_proj,
            'external_proj': self.external_proj,
            'ref_easting': self.ref_easting,
            'ref_northing': self.ref_northing})
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


class OQGeomSerializer(SerializerBase, IOBase):
    """
    Serializes a data structure which later can be consumed by openquake.
    """
    @property
    def _ctx(self):
        return {
            'transform_func': self.transform_func,
            'ramsis_proj': self.ramsis_proj,
            'ref_easting': self.ref_easting,
            'ref_northing': self.ref_northing}

    def _serialize(self, data):
        """
        Serializes a SFM-Worker payload from the ORM into JSON.
        """
        return _SeismicityForecastGeomSchema(context=self._ctx).dump(data)


IOBase.register(SFMWorkerIMessageSerializer)
SerializerBase.register(SFMWorkerIMessageSerializer)
IOBase.register(SFMWorkerOMessageDeserializer)
DeserializerBase.register(SFMWorkerOMessageDeserializer)
