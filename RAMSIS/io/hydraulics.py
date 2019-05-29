# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Utilities for hydraulics data import/export.
"""

import enum
import functools
import io

from marshmallow import (Schema, fields, pre_load, post_load, post_dump,
                         validate, validates_schema, ValidationError, EXCLUDE)

from ramsis.datamodel.hydraulics import Hydraulics, HydraulicSample
from ramsis.datamodel.well import InjectionWell, WellSection
from RAMSIS.io.utils import (DeserializerBase, SerializerBase,
                             IOBase, _IOError)


def validate_positive(d):
    return d >= 0


# XXX(damb): Additional parameter validation to be implemented.
validate_percentage = validate.Range(min=0, max=100)
validate_longitude = validate.Range(min=-180., max=180.)
validate_latitude = validate.Range(min=-90., max=90)
validate_ph = validate.Range(min=0, max=14)

Positive = functools.partial(fields.Float, validate=validate_positive)
Percentage = functools.partial(fields.Float, validate=validate_percentage)
Ph = functools.partial(fields.Float, validate=validate_ph)
Temperature = functools.partial(fields.Float, validate=validate_positive)
Longitude = functools.partial(fields.Float, validate=validate_longitude)
Latitude = functools.partial(fields.Float, validate=validate_latitude)
Depth = Positive
Diameter = Positive
Density = Positive


class HYDWSJSONIOError(_IOError):
    """Base HYDWS-JSON de-/serialization error ({})."""


class _SchemaBase(Schema):
    """
    Schema base class.
    """
    class EContext(enum.Enum):
        """
        Enum collecting schema related contexts.
        """
        PAST = enum.auto()
        FUTURE = enum.auto()

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

    @classmethod
    def _nest_dict(cls, data, sep='_'):
        """
        Nest a dictionary by splitting the key on a delimiter.
        """
        retval = {}
        for k, v in data.items():
            t = retval
            prev = None
            for part in k.split(sep):
                if prev is not None:
                    t = t.setdefault(prev, {})
                prev = part
            else:
                t.setdefault(prev, v)

        return retval

    @classmethod
    def _clear_missing(cls, data):
        retval = data.copy()
        for key in filter(lambda key: data[key] is None, data):
            del retval[key]
        return retval


class _HydraulicSampleSchema(_SchemaBase):
    """
    `Marshmallow <https://marshmallow.readthedocs.io/en/3.0/>`_ schema for an
    hydraulic sample.
    """
    datetime_value = fields.DateTime(format='iso')
    datetime_uncertainty = fields.Float()
    datetime_loweruncertainty = fields.Float()
    datetime_uppearuncertainty = fields.Float()
    datetime_confidencelevel = Percentage()

    bottomtemperature_value = Temperature()
    bottomtemperature_uncertainty = fields.Float()
    bottomtemperature_loweruncertainty = fields.Float()
    bottomtemperature_upperuncertainty = fields.Float()
    bottomtemperature_confidencelevel = Percentage()

    bottomflow_value = fields.Float()
    bottomflow_uncertainty = fields.Float()
    bottomflow_loweruncertainty = fields.Float()
    bottomflow_upperuncertainty = fields.Float()
    bottomflow_confidencelevel = Percentage()

    bottompressure_value = fields.Float()
    bottompressure_uncertainty = fields.Float()
    bottompressure_loweruncertainty = fields.Float()
    bottompressure_upperuncertainty = fields.Float()
    bottompressure_confidencelevel = Percentage()

    toptemperature_value = Temperature()
    toptemperature_uncertainty = fields.Float()
    toptemperature_loweruncertainty = fields.Float()
    toptemperature_upperuncertainty = fields.Float()
    toptemperature_confidencelevel = Percentage()

    topflow_value = fields.Float()
    topflow_uncertainty = fields.Float()
    topflow_loweruncertainty = fields.Float()
    topflow_upperuncertainty = fields.Float()
    topflow_confidencelevel = Percentage()

    toppressure_value = fields.Float()
    toppressure_uncertainty = fields.Float()
    toppressure_loweruncertainty = fields.Float()
    toppressure_upperuncertainty = fields.Float()
    toppressure_confidencelevel = Percentage()

    fluiddensity_value = Density()
    fluiddensity_uncertainty = fields.Float()
    fluiddensity_loweruncertainty = fields.Float()
    fluiddensity_upperuncertainty = fields.Float()
    fluiddensity_confidencelevel = Percentage()

    fluidviscosity_value = fields.Float()
    fluidviscosity_uncertainty = fields.Float()
    fluidviscosity_loweruncertainty = fields.Float()
    fluidviscosity_upperuncertainty = fields.Float()
    fluidviscosity_confidencelevel = Percentage()

    fluidph_value = Ph()
    fluidph_uncertainty = fields.Float()
    fluidph_loweruncertainty = fields.Float()
    fluidph_upperuncertainty = fields.Float()
    fluidph_confidencelevel = Percentage()

    fluidcomposition = fields.String()

    @pre_load
    def flatten(self, data):
        return self._flatten_dict(data)

    @post_load
    def make_object(self, data):
        if self.EContext.PAST in self.context:
            return HydraulicSample(**data)
        return data

    @post_dump
    def nest_fields(self, data):
        if (self.EContext.PAST in self.context or
                self.EContext.FUTURE in self.context):
            return self._nest_dict(self._clear_missing(data))
        return data


class _WellSectionSchema(_SchemaBase):
    """
    `Marshmallow <https://marshmallow.readthedocs.io/en/3.0/>`_ schema for a
    well section.
    """
    TRANSFORM_CALLBACK = None

    starttime = fields.DateTime(format='iso')
    endtime = fields.DateTime(format='iso')

    toplongitude_value = Longitude()
    toplongitude_uncertainty = fields.Float()
    toplongitude_loweruncertainty = fields.Float()
    toplongitude_upperuncertainty = fields.Float()
    toplongitude_confidencelevel = Percentage()

    toplatitude_value = Latitude()
    toplatitude_uncertainty = fields.Float()
    toplatitude_loweruncertainty = fields.Float()
    toplatitude_upperuncertainty = fields.Float()
    toplatitude_confidencelevel = Percentage()

    topdepth_value = Positive()
    topdepth_uncertainty = fields.Float()
    topdepth_loweruncertainty = fields.Float()
    topdepth_upperuncertainty = fields.Float()
    topdepth_confidencelevel = Percentage()

    bottomlongitude_value = Longitude()
    bottomlongitude_uncertainty = fields.Float()
    bottomlongitude_loweruncertainty = fields.Float()
    bottomlongitude_upperuncertainty = fields.Float()
    bottomlongitude_confidencelevel = Percentage()

    bottomlatitude_value = Latitude()
    bottomlatitude_uncertainty = fields.Float()
    bottomlatitude_loweruncertainty = fields.Float()
    bottomlatitude_upperuncertainty = fields.Float()
    bottomlatitude_confidencelevel = Percentage()

    bottomdepth_value = Positive()
    bottomdepth_uncertainty = fields.Float()
    bottomdepth_loweruncertainty = fields.Float()
    bottomdepth_upperuncertainty = fields.Float()
    bottomdepth_confidencelevel = Percentage()

    holediameter_value = Diameter()
    holediameter_uncertainty = fields.Float()
    holediameter_loweruncertainty = fields.Float()
    holediameter_upperuncertainty = fields.Float()
    holediameter_confidencelevel = Percentage()

    casingdiameter_value = Diameter()
    casingdiameter_uncertainty = fields.Float()
    casingdiameter_loweruncertainty = fields.Float()
    casingdiameter_upperuncertainty = fields.Float()
    casingdiameter_confidencelevel = Percentage()

    topclosed = fields.Boolean()
    bottomclosed = fields.Boolean()
    sectiontype = fields.String()
    casingtype = fields.String()
    description = fields.String()

    publicid = fields.String()

    hydraulics = fields.Method('_serialize_hydraulics',
                               deserialize='_deserialize_hydraulics')

    def _serialize_hydraulics(self, obj):
        serializer = _HydraulicSampleSchema(many=True, context=self.context)
        if self.EContext.PAST in self.context:
            return serializer.dump(obj.hydraulics.samples)
        elif self.EContext.FUTURE in self.context:
            return serializer.dump(obj.injectionplan.samples)

        raise HYDWSJSONIOError('Invalid context.')

    def _deserialize_hydraulics(self, value):
        # XXX(damb): Load from HYDWS
        return _HydraulicSampleSchema(
            many=True, context=self.context).load(value)

    @pre_load
    def flatten(self, data):
        return self._flatten_dict(data)

    @post_load
    def load_postprocess(self, data):
        return self.make_object(self._transform(data))

    @post_dump
    def dump_postprocess(self, data):
        if (self.EContext.PAST in self.context or
                self.EContext.FUTURE in self.context):
            return self._nest_dict(self._clear_missing(self._transform(data)))
        return data

    @validates_schema
    def validate_sections(self, data):
        if len(data['hydraulics']) < 1:
            raise ValidationError(
                'At least a single sample required.')

    def make_object(self, data):
        if self.EContext.PAST in self.context:
            # XXX(damb): Wrap samples with Hydraulics envelope
            if 'hydraulics' in data:
                data['hydraulics'] = Hydraulics(samples=data['hydraulics'])
            return WellSection(**data)
        return data

    def _transform(self, data):
        transform_func = self._transform_callback
        if 'transform_callback' in self.context:
            transform_func = self.context['transform_callback']

        try:
            data['toplongitude_value'], \
                data['toplatitude_value'], \
                data['topdepth_value'] = transform_func(
                data['toplongitude_value'],
                data['toplatitude_value'],
                data['topdepth_value'])
            data['bottomlongitude_value'], \
                data['bottomlatitude_value'], \
                data['bottomdepth_value'] = transform_func(
                data['bottomlongitude_value'],
                data['bottomlatitude_value'],
                data['bottomdepth_value'])
        except (TypeError, ValueError, AttributeError) as err:
            raise ValidationError(
                f"Error while transforming coordinates: {err}")

        return data

    @staticmethod
    def _transform_callback(x, y, z):
        """
        Template method implementing the default transformation rule (i.e. no
        transformation).
        """
        return x, y, z


class _InjectionWellSchema(_SchemaBase):
    """
    `Marshmallow <https://marshmallow.readthedocs.io/en/3.0/>`_ schema for an
    injection well.
    """
    publicid = fields.String()

    sections = fields.Nested(_WellSectionSchema, many=True)

    @post_load
    def make_object(self, data):
        if self.EContext.PAST in self.context:
            return InjectionWell(**data)
        return data

    @validates_schema
    def validate_sections(self, data):
        if len(data['sections']) != 1:
            raise ValidationError(
                'InjectionWells are required to have a single section.')

    class Meta:
        unknown = EXCLUDE


# -----------------------------------------------------------------------------
class HYDWSBoreholeHydraulicsDeserializer(DeserializerBase, IOBase):
    """
    Deserializes borehole and hydraulics data to be used together with the
    RT-RAMSIS data model.
    """
    # TODO(damb): Due to the JSON response format of HYDWS (more concretely,
    # referring to its hierarchical structure) parsing the response iteratevly
    # does not appear to be adequate. That is why for the moment we simply
    # implement a *bulk* deserializer.
    SRS_EPSG = 4326

    LOGGER = 'RAMSIS.io.hydwsboreholehydraulicsdeserializer'

    def __init__(self, **kwargs):
        """
        :param str proj: Spatial reference system in Proj4 notation
            representing the local coordinate system
        :param transform_callback: Function reference for transforming data
            into local coordinate system
        """
        super().__init__(**kwargs)

        self._proj = kwargs.get('proj')
        if not self._proj:
            raise HYDWSJSONIOError("Missing SRS (PROJ4) projection.")

    @property
    def proj(self):
        return self._proj

    def _deserialize(self, data):
        """
        Deserializes borehole hydraulic data received from HYDWS to RT-RAMSIS
        ORM.

        :param data: Data to be deserialized

        :returns: Borehole ORM representation
        :rtype: :py:class:`ramsis.datamodel.well.InjectionWell`
        """
        # XXX(damb): Pass transformation rule/function by means of the
        # ma.Schema context
        crs_transform = self._transform_callback or self._transform
        ctx = {
            _SchemaBase.EContext.PAST: True,
            'transform_callback': functools.partial(
                crs_transform, source_proj=self.SRS_EPSG,
                target_proj=self.proj)}
        return _InjectionWellSchema(context=ctx).loads(data)


class HYDWSBoreholeHydraulicsSerializer(SerializerBase, IOBase):
    """
    Serializes borehole and hydraulics data from the RT-RAMSIS data model.
    """

    SRS_EPSG = 4326

    def __init__(self, **kwargs):
        """
        :param str proj: Spatial reference system in Proj4 notation
            representing the local coordinate system
        :param transform_callback: Function reference for transforming data
            into local coordinate system
        """
        super().__init__(**kwargs)

        self._proj = kwargs.get('proj')
        if not self._proj:
            raise HYDWSJSONIOError("Missing SRS (PROJ4) projection.")

        self._ctx = ({_SchemaBase.EContext.FUTURE: True}
                     if kwargs.get('plan', False) else
                     {_SchemaBase.EContext.PAST: True})

    def _serialize(self, data):
        """
        Serializes borehole hydraulic data from the ORM into an HYDWS conform
        JSON format.

        :param data: Injection well to be serialized
        :type data: :py:class:`ramsis.datamodel.hydraulics.InjectionWell`
        """
        crs_transform = self._transform_callback or self._transform
        ctx = {
            'transform_callback': functools.partial(
                crs_transform, source_proj=self._proj,
                target_proj=self.SRS_EPSG)}
        ctx.update(self._ctx)
        return _InjectionWellSchema(context=ctx).dump(data)


IOBase.register(HYDWSBoreholeHydraulicsDeserializer)
IOBase.register(HYDWSBoreholeHydraulicsSerializer)
DeserializerBase.register(HYDWSBoreholeHydraulicsDeserializer)
SerializerBase.register(HYDWSBoreholeHydraulicsSerializer)
