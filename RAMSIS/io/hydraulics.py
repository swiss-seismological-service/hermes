# Copyright i2019, ETH Zurich - Swiss Seismological Service SED
"""
Utilities for hydraulics data import/export.
"""
import logging
import enum
import functools

from marshmallow import (Schema, fields, pre_load, post_load, post_dump,
                         pre_dump, validate, validates_schema,
                         ValidationError, EXCLUDE)

from ramsis.datamodel.hydraulics import (Hydraulics, InjectionPlan,
                                         HydraulicSample)
from ramsis.datamodel.well import InjectionWell, WellSection
from RAMSIS.io.utils import (DeserializerBase, SerializerBase,
                             IOBase, _IOError, TransformationError, Positive,
                             DateTime, Percentage, Uncertainty,
                             validate_positive, append_ms_zeroes)

logger = logging.getLogger(__name__)

# XXX(damb): Additional parameter validation to be implemented.
validate_longitude = validate.Range(min=-180., max=180.)
validate_latitude = validate.Range(min=-90., max=90)
validate_ph = validate.Range(min=0, max=14)

Ph = functools.partial(fields.Float, validate=validate_ph)
Temperature = functools.partial(fields.Float, validate=validate_positive)
Longitude = functools.partial(fields.Float, validate=validate_longitude)
Latitude = functools.partial(fields.Float, validate=validate_latitude)
Depth = Positive
Diameter = Positive
Density = Positive
Viscosity = Positive


class HYDWSJSONIOError(_IOError):
    """Base HYDWS-JSON de-/serialization error ({})."""


class _SchemaBase(Schema):
    """
    Schema base class.
    """
    class Meta:
        ordered = True

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
    datetime_value = DateTime(required=True)
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

    fluidviscosity_value = Viscosity()
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
    def pre_process(self, data, **kwargs):
        data = self._flatten_dict(data)
        data = self._clear_missing(data)
        if 'datetime_value' in data:
            data['datetime_value'] = append_ms_zeroes(data['datetime_value'])

        return data

    @post_load
    def make_object(self, data, **kwargs):
        if ('time' in self.context and
                self.context['time'] in (self.EContext.PAST,
                                         self.EContext.FUTURE)):
            return HydraulicSample(**data)
        return data

    @post_dump
    def nest_fields(self, data, **kwargs):
        if 'datetime_value' in data:
            data['datetime_value'] = append_ms_zeroes(data['datetime_value'])

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
    starttime = DateTime()
    endtime = DateTime()

    topx_value = Longitude(required=True, data_key='toplongitude_value')
    topx_uncertainty = Uncertainty(data_key='toplongitude_uncertainty')
    topx_loweruncertainty = Uncertainty(
        data_key='toplongitude_loweruncertainty')
    topx_upperuncertainty = Uncertainty(
        data_key='toplongitude_upperuncertainty')
    topx_confidencelevel = Percentage(
        data_key='toplongitude_confidencelevel')

    topy_value = Latitude(required=True, data_key='toplatitude_value')
    topy_uncertainty = Uncertainty(
        data_key='toplatitude_uncertainty')
    topy_loweruncertainty = Uncertainty(
        data_key='toplatitude_loweruncertainty')
    topy_upperuncertainty = Uncertainty(
        data_key='toplatitude_upperuncertainty')
    topy_confidencelevel = Percentage(data_key='toplatitude_confidencelevel')

    topz_value = Depth(required=True, data_key='topdepth_value')
    topz_uncertainty = Uncertainty(data_key='topdepth_uncertainty')
    topz_loweruncertainty = Uncertainty(
        data_key='topdepth_loweruncertainty')
    topz_upperuncertainty = Uncertainty(
        data_key='topdepth_upperuncertainty')
    topz_confidencelevel = Percentage(
        data_key='topdepth_confidencelevel')

    bottomx_value = Longitude(
        required=True, data_key='bottomlongitude_value')
    bottomx_uncertainty = Uncertainty(
        data_key='bottomlongitude_uncertainty')
    bottomx_loweruncertainty = Uncertainty(
        data_key='bottomlongitude_loweruncertainty')
    bottomx_upperuncertainty = Uncertainty(
        data_key='bottomlongitude_upperuncertainty')
    bottomx_confidencelevel = Percentage(
        data_key='bottomlongitude_confidencelevel')

    bottomy_value = Latitude(
        required=True, data_key='bottomlatitude_value')
    bottomy_uncertainty = Uncertainty(
        data_key='bottomlatitude_uncertainty')
    bottomy_loweruncertainty = Uncertainty(
        data_key='bottomlatitude_loweruncertainty')
    bottomy_upperuncertainty = Uncertainty(
        data_key='bottomlatitude_upperuncertainty')
    bottomy_confidencelevel = Percentage(
        data_key='bottomlatitude_confidencelevel')

    bottomz_value = Depth(
        required=True, data_key='bottomdepth_value')
    bottomz_uncertainty = Uncertainty(
        data_key='bottomdepth_uncertainty')
    bottomz_loweruncertainty = Uncertainty(
        data_key='bottomdepth_loweruncertainty')
    bottomz_upperuncertainty = Uncertainty(
        data_key='bottomdepth_upperuncertainty')
    bottomz_confidencelevel = Percentage(
        data_key='bottomdepth_confidencelevel')

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
            if (self.context['time'] is self.EContext.PAST and
                    obj.hydraulics is not None):
                return serializer.dump(obj.hydraulics.samples)
            elif (self.context['time'] is self.EContext.FUTURE and
                    obj.injectionplan is not None):
                return serializer.dump(obj.injectionplan.samples)

            return None

        raise HYDWSJSONIOError('Invalid context.')

    def _deserialize_hydraulics(self, value):
        # XXX(damb): Load from HYDWS
        return _HydraulicSampleSchema(
            many=True, context=self.context).load(value)

    @pre_load
    def load_preprocess(self, data, **kwargs):
        if ('time' in self.context and
            self.context['time'] in (self.EContext.PAST,
                                     self.EContext.FUTURE)):
            data = self._flatten_dict(data)

        if 'starttime' in data:
            data['starttime'] = append_ms_zeroes(data['starttime'])

        if 'endtime' in data:
            data['endtime'] = append_ms_zeroes(data['endtime'])

        return data

    @post_load
    def load_postprocess(self, data, **kwargs):
        if ('time' in self.context and
            self.context['time'] in (self.EContext.PAST,
                                     self.EContext.FUTURE)):
            data = self.make_object(data)

            data = self._transform_load(data)
        return data

    @post_dump
    def dump_postprocess(self, data, **kwargs):
        if ('time' in self.context and
            self.context['time'] in (self.EContext.PAST,
                                     self.EContext.FUTURE)):
            data = self._transform_dump(data)
            return self._nest_dict(self._clear_missing(data))

        if 'starttime' in data:
            data['starttime'] = append_ms_zeroes(data['starttime'])

        if 'endtime' in data:
            data['endtime'] = append_ms_zeroes(data['endtime'])
        return data

    @validates_schema
    def validate_sections(self, data, **kwargs):
        if ('time' in self.context and
            self.context['time'] is self.EContext.PAST and
                'hydraulics' in data and len(data['hydraulics']) < 1):
            raise ValidationError(
                'At least a single sample required.')

    def make_object(self, data):
        if 'time' in self.context:
            if 'hydraulics' in data:
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

    def _transform_load(self, data):
        """
        Transform coordinates from external to local coordinates.
        """
        transform_func = self.context['transform_func']
        if 'altitude_value' not in self.context.keys():
            raise ValidationError(
                'Transformation of well coordinates cannot take place'
                ' as altitude is not given')

        altitude_value = self.context['altitude_value']
        # +z values have a directionality as depth
        topz_value = data.topz_value if data.topz_value else 0
        bottomz_value = data.bottomz_value if data.bottomz_value else 0
        topdepth_value = -altitude_value + topz_value
        bottomdepth_value = -altitude_value + bottomz_value
        # The input values have an expected directionality of
        # x, y, depth = lat, lon, depth
        # The output values to a local CRS have an expected directionality of
        # x, y, z = easting, northing, height

        try:
            (data.topx_value,
             data.topy_value,
             data.topz_value) = transform_func(
                data.topx_value,
                data.topy_value,
                topdepth_value)
            (data.bottomx_value,
             data.bottomy_value,
             data.bottomz_value) = transform_func(
                data.bottomx_value,
                data.bottomy_value,
                bottomdepth_value)
        except (TypeError, ValueError, AttributeError) as err:
            raise TransformationError(f"{err}")
        return data

    def _validate_transform(self, data):
        errors = {}
        for prefix in ['top', 'bottom']:
            lon = data[f"{prefix}longitude_value"]
            lat = data[f"{prefix}latitude_value"]
            depth = data[f"{prefix}depth_value"]
            if lon > 180.0 or lon < -180.0:
                errors[f"{prefix}longitude_value"] = [
                    f'Hydraulic section {prefix}longitude is not within '
                    f'boundaries {lon}']
            if lat > 90.0 or lat < -90.0:
                errors[f"{prefix}latitude_value"] = [
                    f'Hydraulic section {prefix}latitude is not within '
                    f'boundaries {lat}']
            if depth < 0.0:
                errors[f"{prefix}depth_value"] = [
                    f'Hydraulic section {prefix}depth is not within '
                    f'boundaries {depth}']
        if errors:
            raise ValidationError(errors)
        return data

    def _transform_dump(self, data):
        """
        Transform coordinates from local to external coordinates.
        """
        # sarsonl Although not nice, for speed it is good to do
        # the transform after the data has been serialized. This is becuase
        # if the data is stil an object, this interferes with the process
        # of writing the snapshot to the db (which happens in parallel).
        # It is not nice because although the data is called
        # latitude/longitude/depth
        # it is actually still x, y, z local coords which is confusing.
        transform_func = self.context['transform_func']
        if 'altitude_value' not in self.context.keys():
            raise ValidationError(
                'Transformation of well coordinates cannot take place'
                ' as altitude is not given')
        try:
            (data["toplongitude_value"],
             data["toplatitude_value"],
             topdepth_value) = transform_func(
                data["toplongitude_value"],
                data["toplatitude_value"],
                data["topdepth_value"])
            (data["bottomlongitude_value"],
             data["bottomlatitude_value"],
             bottomdepth_value) = transform_func(
                data["bottomlongitude_value"],
                data["bottomlatitude_value"],
                data["bottomdepth_value"])

        except (TypeError, ValueError, AttributeError) as err:
            raise TransformationError(f"{err}")

        altitude_value = self.context['altitude_value']
        topdepth_value = topdepth_value if topdepth_value else 0
        bottomdepth_value = bottomdepth_value if bottomdepth_value else 0
        data["topdepth_value"] = altitude_value + topdepth_value
        data["bottomdepth_value"] = altitude_value + bottomdepth_value

        return data


class _InjectionWellSchema(_SchemaBase):
    """
    `Marshmallow <https://marshmallow.readthedocs.io/en/3.0/>`_ schema for an
    injection well.
    """
    bedrockdepth_value = Depth()
    bedrockdepth_uncertainty = Uncertainty()
    bedrockdepth_loweruncertainty = Uncertainty()
    bedrockdepth_upperuncertainty = Uncertainty()
    bedrockdepth_confidencelevel = Percentage()

    altitude_value = fields.Float(required=True)
    altitude_uncertainty = Uncertainty()
    altitude_loweruncertainty = Uncertainty()
    altitude_upperuncertainty = Uncertainty()
    altitude_confidencelevel = Percentage()

    publicid = fields.String()

    sections = fields.Nested(_WellSectionSchema, many=True)

    def update_context(self, key, value):
        self.context[key] = value

    @pre_load
    def preload_data(self, data, **kwargs):
        data = self.flatten(data, **kwargs)
        if len(data['sections']) == 0:
            raise ValidationError(
                'Hydraulic data has no sections')
        elif len(data['sections']) > 1:
            data = self.remove_extra_sections(data, **kwargs)
        return data

    def flatten(self, data, **kwargs):
        if ('time' in self.context and
            self.context['time'] in (self.EContext.PAST,
                                     self.EContext.FUTURE)):
            data = self._flatten_dict(data)
        if 'altitude_value' in data.keys():
            self.update_context('altitude_value', data['altitude_value'])
        return data

    @post_load
    def make_object(self, data, **kwargs):
        if ('time' in self.context and
                self.context['time'] in (self.EContext.PAST,
                                         self.EContext.FUTURE)):
            return InjectionWell(**data)
        return data

    @pre_dump
    def add_altitude_context(self, data, **kwargs):
        altitude_value = None
        try:
            if data:
                altitude_value = data.altitude_value
        except AttributeError as err:
            raise ValidationError(
                f'Injection well has no altitude value. {err}')
        if altitude_value is not None:
            self.update_context('altitude_value', altitude_value)
        return data

    @post_dump
    def dump_postprocess(self, data, **kwargs):
        if ('time' in self.context and
            self.context['time'] in (self.EContext.PAST,
                                     self.EContext.FUTURE)):
            return self._nest_dict(self._clear_missing(data))
        return data

    def remove_extra_sections(self, data, **kwargs):
        logger.warning(
            f"Well has multiple sections {len(data['sections'])},"
            'reducing to first '
            'valid section with hydraulic samples.')
        data['sections'].sort(key=lambda x: x['starttime'])
        data['sections'] = [data['sections'][0]]
        logger.info(
            "Using section with starttime:"
            f"{data['sections'][0]['starttime']}")
        logger.info(
            "Number of hydraulics in section: "
            f"{len(data['sections'][0]['hydraulics'])}")
        return data

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

    LOGGER = 'RAMSIS.io.hydwsboreholehydraulicsdeserializer'

    def __init__(self, **kwargs):
        """
        :param transform_func: Function reference for transforming data
            into local coordinate system
        """
        super().__init__(**kwargs)
        self.__ctx = kwargs
        self.__ctx.update({'time': _SchemaBase.EContext.FUTURE}
                          if kwargs.get('plan', False) else
                          {'time': _SchemaBase.EContext.PAST})
        self.__ctx.update({'transform_func': self.transform_func})

    @property
    def _ctx(self):
        # XXX(damb): Pass transformation rule/function by means of the
        # ma.Schema context
        return self.__ctx

    def _deserialize(self, data):
        """
        Deserializes borehole hydraulic data received from HYDWS to RT-RAMSIS
        ORM.

        :param data: Data to be deserialized

        :returns: Borehole ORM representation
        :rtype: :py:class:`ramsis.datamodel.well.InjectionWell`

        :raises: :py:class:`HYDWSJSONIOError` if deserialization fails
        """
        try:
            return _InjectionWellSchema(context=self._ctx).loads(data)
        except ValidationError as err:
            raise HYDWSJSONIOError(err)

    def _loado(self, data):
        return _InjectionWellSchema(context=self._ctx).load(data)


class HYDWSBoreholeHydraulicsSerializer(SerializerBase, IOBase):
    """
    Serializes borehole and hydraulics data from the RT-RAMSIS data model.
    """

    def __init__(self, **kwargs):
        """
        :param transform_func: Function reference for transforming data
            into local coordinate system
        """
        super().__init__(**kwargs)
        self.__ctx = kwargs
        self.__ctx.update({'time': _SchemaBase.EContext.FUTURE}
                          if kwargs.get('plan', False) else
                          {'time': _SchemaBase.EContext.PAST})
        self.__ctx.update({'transform_func': self.transform_func})

    @property
    def _ctx(self):
        return self.__ctx

    def _serialize(self, data):
        """
        Serializes borehole hydraulic data from the ORM into an HYDWS conform
        JSON format.

        :param data: Injection well to be serialized
        :type data: :py:class:`ramsis.datamodel.hydraulics.InjectionWell`

        :rtype: str
        """
        return _InjectionWellSchema(context=self._ctx).dumps(data)

    def _dumpo(self, data):
        return _InjectionWellSchema(context=self._ctx).dump(data)


IOBase.register(HYDWSBoreholeHydraulicsDeserializer)
IOBase.register(HYDWSBoreholeHydraulicsSerializer)
DeserializerBase.register(HYDWSBoreholeHydraulicsDeserializer)
SerializerBase.register(HYDWSBoreholeHydraulicsSerializer)
