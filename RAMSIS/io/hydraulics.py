# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Utilities for hydraulics data import/export.
"""

import enum
import functools

from marshmallow import (Schema, fields, pre_load, post_load, post_dump,
                         validate, validates_schema, ValidationError, EXCLUDE)

from ramsis.datamodel.hydraulics import (Hydraulics, InjectionPlan,
                                         HydraulicSample)
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
Uncertainty = Positive


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
    datetime_value = fields.DateTime(format='iso', required=True)
    datetime_uncertainty = Uncertainty()
    datetime_loweruncertainty = Uncertainty()
    datetime_uppearuncertainty = Uncertainty()
    datetime_confidencelevel = Percentage()

    bottomtemperature_value = Temperature()
    bottomtemperature_uncertainty = Uncertainty()
    bottomtemperature_loweruncertainty = Uncertainty()
    bottomtemperature_upperuncertainty = Uncertainty()
    bottomtemperature_confidencelevel = Percentage()

    bottomflow_value = fields.Float()
    bottomflow_uncertainty = Uncertainty()
    bottomflow_loweruncertainty = Uncertainty()
    bottomflow_upperuncertainty = Uncertainty()
    bottomflow_confidencelevel = Percentage()

    bottompressure_value = fields.Float()
    bottompressure_uncertainty = Uncertainty()
    bottompressure_loweruncertainty = Uncertainty()
    bottompressure_upperuncertainty = Uncertainty()
    bottompressure_confidencelevel = Percentage()

    toptemperature_value = Temperature()
    toptemperature_uncertainty = Uncertainty()
    toptemperature_loweruncertainty = Uncertainty()
    toptemperature_upperuncertainty = Uncertainty()
    toptemperature_confidencelevel = Percentage()

    topflow_value = fields.Float()
    topflow_uncertainty = Uncertainty()
    topflow_loweruncertainty = Uncertainty()
    topflow_upperuncertainty = Uncertainty()
    topflow_confidencelevel = Percentage()

    toppressure_value = fields.Float()
    toppressure_uncertainty = Uncertainty()
    toppressure_loweruncertainty = Uncertainty()
    toppressure_upperuncertainty = Uncertainty()
    toppressure_confidencelevel = Percentage()

    fluiddensity_value = Density()
    fluiddensity_uncertainty = Uncertainty()
    fluiddensity_loweruncertainty = Uncertainty()
    fluiddensity_upperuncertainty = Uncertainty()
    fluiddensity_confidencelevel = Percentage()

    fluidviscosity_value = fields.Float()
    fluidviscosity_uncertainty = Uncertainty()
    fluidviscosity_loweruncertainty = Uncertainty()
    fluidviscosity_upperuncertainty = Uncertainty()
    fluidviscosity_confidencelevel = Percentage()

    fluidph_value = Ph()
    fluidph_uncertainty = Uncertainty()
    fluidph_loweruncertainty = Uncertainty()
    fluidph_upperuncertainty = Uncertainty()
    fluidph_confidencelevel = Percentage()

    fluidcomposition = fields.String()

    @pre_load
    def flatten(self, data):
        return self._flatten_dict(data)

    @post_load
    def make_object(self, data):
        if ('time' in self.context and
                self.context['time'] in (self.EContext.PAST,
                                         self.EContext.FUTURE)):
            return HydraulicSample(**data)
        return data

    @post_dump
    def nest_fields(self, data):
        if ('time' in self.context and
            self.context['time'] in (self.EContext.PAST,
                                     self.EContext.FUTURE)):
            return self._nest_dict(self._clear_missing(data))
        return data


class _WellSectionSchema(_SchemaBase):
    """
    `Marshmallow <https://marshmallow.readthedocs.io/en/3.0/>`_ schema for a
    well section.
    """
    starttime = fields.DateTime(format='iso')
    endtime = fields.DateTime(format='iso')

    toplongitude_value = Longitude(required=True)
    toplongitude_uncertainty = Uncertainty()
    toplongitude_loweruncertainty = Uncertainty()
    toplongitude_upperuncertainty = Uncertainty()
    toplongitude_confidencelevel = Percentage()

    toplatitude_value = Latitude(required=True)
    toplatitude_uncertainty = Uncertainty()
    toplatitude_loweruncertainty = Uncertainty()
    toplatitude_upperuncertainty = Uncertainty()
    toplatitude_confidencelevel = Percentage()

    topdepth_value = Depth(required=True)
    topdepth_uncertainty = Uncertainty()
    topdepth_loweruncertainty = Uncertainty()
    topdepth_upperuncertainty = Uncertainty()
    topdepth_confidencelevel = Percentage()

    bottomlongitude_value = Longitude(required=True)
    bottomlongitude_uncertainty = Uncertainty()
    bottomlongitude_loweruncertainty = Uncertainty()
    bottomlongitude_upperuncertainty = Uncertainty()
    bottomlongitude_confidencelevel = Percentage()

    bottomlatitude_value = Latitude(required=True)
    bottomlatitude_uncertainty = Uncertainty()
    bottomlatitude_loweruncertainty = Uncertainty()
    bottomlatitude_upperuncertainty = Uncertainty()
    bottomlatitude_confidencelevel = Percentage()

    bottomdepth_value = Depth(required=True)
    bottomdepth_uncertainty = Uncertainty()
    bottomdepth_loweruncertainty = Uncertainty()
    bottomdepth_upperuncertainty = Uncertainty()
    bottomdepth_confidencelevel = Percentage()

    holediameter_value = Diameter()
    holediameter_uncertainty = Uncertainty()
    holediameter_loweruncertainty = Uncertainty()
    holediameter_upperuncertainty = Uncertainty()
    holediameter_confidencelevel = Percentage()

    casingdiameter_value = Diameter()
    casingdiameter_uncertainty = Uncertainty()
    casingdiameter_loweruncertainty = Uncertainty()
    casingdiameter_upperuncertainty = Uncertainty()
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
        if 'time' in self.context:
            if self.context['time'] is self.EContext.PAST:
                return serializer.dump(obj.hydraulics.samples)
            elif self.context['time'] is self.EContext.FUTURE:
                return serializer.dump(obj.injectionplan.samples)

        raise HYDWSJSONIOError('Invalid context.')

    def _deserialize_hydraulics(self, value):
        # XXX(damb): Load from HYDWS
        return _HydraulicSampleSchema(
            many=True, context=self.context).load(value)

    @pre_load
    def flatten(self, data):
        if ('time' in self.context and
            self.context['time'] in (self.EContext.PAST,
                                     self.EContext.FUTURE)):
            return self._flatten_dict(data)
        return data

    @post_load
    def load_postprocess(self, data):
        if ('time' in self.context and
            self.context['time'] in (self.EContext.PAST,
                                     self.EContext.FUTURE)):
            if self.context.get('proj'):
                data = self._transform(data)
            return self.make_object(data)
        return data

    @post_dump
    def dump_postprocess(self, data):
        if ('time' in self.context and
            self.context['time'] in (self.EContext.PAST,
                                     self.EContext.FUTURE)):
            if self.context.get('proj'):
                data = self._transform(data)
            return self._nest_dict(self._clear_missing(data))
        return data

    @validates_schema
    def validate_sections(self, data):
        if ('time' in self.context and
            self.context['time'] is self.EContext.PAST and
                len(data['hydraulics']) < 1):
            raise ValidationError(
                'At least a single sample required.')

    def make_object(self, data):
        if 'time' in self.context and 'hydraulics' in data:
            if self.context['time'] is self.EContext.PAST:
                # XXX(damb): Wrap samples with Hydraulics envelope
                data['hydraulics'] = Hydraulics(samples=data['hydraulics'])
            elif self.context['time'] is self.EContext.FUTURE:
                # XXX(damb): Wrap samples with InjectionPlan envelope
                data['injectionplan'] = InjectionPlan(
                    samples=data['hydraulics'])
                del data['hydraulics']

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
    bedrockdepth_value = Depth(required=True)
    bedrockdepth_uncertainty = Uncertainty()
    bedrockdepth_loweruncertainty = Uncertainty()
    bedrockdepth_upperuncertainty = Uncertainty()
    bedrockdepth_confidencelevel = Percentage()

    publicid = fields.String()

    sections = fields.Nested(_WellSectionSchema, many=True)

    @pre_load
    def flatten(self, data):
        if ('time' in self.context and
            self.context['time'] in (self.EContext.PAST,
                                     self.EContext.FUTURE)):
            return self._flatten_dict(data)
        return data

    @post_load
    def make_object(self, data):
        if ('time' in self.context and
                self.context['time'] in (self.EContext.PAST,
                                         self.EContext.FUTURE)):
            return InjectionWell(**data)
        return data

    @post_dump
    def dump_postprocess(self, data):
        if ('time' in self.context and
            self.context['time'] in (self.EContext.PAST,
                                     self.EContext.FUTURE)):
            return self._nest_dict(self._clear_missing(data))
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

    def __init__(self, proj=None, **kwargs):
        """
        :param proj: Spatial reference system in Proj4 notation
            representing the local coordinate system
        :type proj: str or None
        :param transform_callback: Function reference for transforming data
            into local coordinate system
        """
        super().__init__(**kwargs)

        self._proj = proj

        self._ctx = ({'time': _SchemaBase.EContext.FUTURE}
                     if kwargs.get('plan', False) else
                     {'time': _SchemaBase.EContext.PAST})

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
            'proj': self.proj,
            'transform_callback': functools.partial(
                crs_transform, source_proj=self.SRS_EPSG,
                target_proj=self.proj)}
        ctx.update(self._ctx)
        return _InjectionWellSchema(context=ctx).loads(data)


class HYDWSBoreholeHydraulicsSerializer(SerializerBase, IOBase):
    """
    Serializes borehole and hydraulics data from the RT-RAMSIS data model.
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
        super().__init__(**kwargs)

        self._proj = proj

        self._ctx = ({'time': _SchemaBase.EContext.FUTURE}
                     if kwargs.get('plan', False) else
                     {'time': _SchemaBase.EContext.PAST})

    def _serialize(self, data):
        """
        Serializes borehole hydraulic data from the ORM into an HYDWS conform
        JSON format.

        :param data: Injection well to be serialized
        :type data: :py:class:`ramsis.datamodel.hydraulics.InjectionWell`

        :rtype: str
        """
        crs_transform = self._transform_callback or self._transform
        ctx = {
            'proj': self._proj,
            'transform_callback': functools.partial(
                crs_transform, source_proj=self._proj,
                target_proj=self.SRS_EPSG)}
        ctx.update(self._ctx)
        return _InjectionWellSchema(context=ctx).dumps(data)


IOBase.register(HYDWSBoreholeHydraulicsDeserializer)
IOBase.register(HYDWSBoreholeHydraulicsSerializer)
DeserializerBase.register(HYDWSBoreholeHydraulicsDeserializer)
SerializerBase.register(HYDWSBoreholeHydraulicsSerializer)
