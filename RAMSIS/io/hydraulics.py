# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Utitlities for hydraulics data import.
"""

import enum
import functools
import io

from marshmallow import Schema, fields, post_load, ValidationError, EXCLUDE

from ramsis.datamodel.hydraulics import Hydraulics, HydraulicSample
from ramsis.datamodel.well import InjectionWell, WellSection
from RAMSIS.io.utils import DeserializerBase, IOBase, _IOError


class HYDWSJSONIOError(_IOError):
    """Base HYDJSON de-/serialization error ({})."""


class SchemaBase(Schema):
    """
    Schema base class.
    """
    __SEP = '_'

    class EContext(enum.Enum):
        """
        Enum collecting schema related contexts.
        """
        ORM = enum.auto()

    def _flatten_object(self, data, as_flat_fields):
        for f in as_flat_fields:
            if f in data:
                for k, v in data[f].items():
                    data[f + self.__SEP + k] = v

                del data[f]

        return data


class QuakeMLQuantityTypeBase(SchemaBase):
    """
    Base class for `QuakeML <https://quake.ethz.ch/quakeml/>`_
    :code:`*Quantity` type schemas.
    """
    uncertainty = fields.Float()
    loweruncertainty = fields.Float()
    upperuncertainty = fields.Float()
    confidencelevel = fields.Float()


class QuakeMLRealQuantityType(QuakeMLQuantityTypeBase):
    """
    Implementation of a `QuakeML <https://quake.ethz.ch/quakeml/>`_
    :code:`RealQuantity` type schema.
    """
    value = fields.Float()


class QuakeMLTimeQuantityType(QuakeMLQuantityTypeBase):
    """
    Implementation of a `QuakeML <https://quake.ethz.ch/quakeml/>`_
    :code:`TimeQuantity` type schema.
    """
    value = fields.DateTime(format='iso')


class HydraulicSampleSchema(SchemaBase):
    """
    `Marshmallow <https://marshmallow.readthedocs.io/en/3.0/>`_ schema for an
    hydraulic sample.
    """
    # TODO(damb): Check if there is a more elegant implementation instead of
    # the cumbersome, redundant declaration of QuakeML type attributes. Maybe,
    # something like SQLAlchemy's declared_attr implementation could give some
    # ideas.
    # XXX(damb): for context depended flattening
    __QUAKEML_TYPES = (
        'datetime',
        'bottomtemperature',
        'bottomflow',
        'bottompressure',
        'toptemperature',
        'topflow',
        'toppressure',
        'fluiddensity',
        'fluidviscosity',
        'fluidph', )

    datetime = fields.Nested(QuakeMLTimeQuantityType)
    bottomtemperature = fields.Nested(QuakeMLRealQuantityType)
    bottomflow = fields.Nested(QuakeMLRealQuantityType)
    bottompressure = fields.Nested(QuakeMLRealQuantityType)
    toptemperature = fields.Nested(QuakeMLRealQuantityType)
    topflow = fields.Nested(QuakeMLRealQuantityType)
    toppressure = fields.Nested(QuakeMLRealQuantityType)
    fluiddensity = fields.Nested(QuakeMLRealQuantityType)
    fluidviscosity = fields.Nested(QuakeMLRealQuantityType)
    fluidph = fields.Nested(QuakeMLRealQuantityType)
    fluidcomposition = fields.String()

    @post_load
    def make_object(self, data):
        if self.EContext.ORM in self.context:
            return HydraulicSample(
                **self._flatten_object(data, self.__QUAKEML_TYPES))
        return data


class WellSectionSchema(SchemaBase):
    """
    `Marshmallow <https://marshmallow.readthedocs.io/en/3.0/>`_ schema for a
    well section.
    """
    # TODO(damb): Check if there is a more elegant implementation instead of
    # the cumbersome, redundant declaration of QuakeML type attributes. Maybe,
    # something like SQLAlchemy's declared_attr implementation could give some
    # ideas.
    # XXX(damb): for context depended flattening
    TRANSFORM_CALLBACK = None
    __QUAKEML_TYPES = (
        'toplongitude',
        'toplatitude',
        'topdepth',
        'bottomlongitude',
        'bottomlatitude',
        'bottomdepth',
        'holediameter',
        'casingdiameter', )

    starttime = fields.DateTime(format='iso')
    endtime = fields.DateTime(format='iso')
    toplongitude = fields.Nested(QuakeMLRealQuantityType)
    toplatitude = fields.Nested(QuakeMLRealQuantityType)
    topdepth = fields.Nested(QuakeMLRealQuantityType)
    bottomlongitude = fields.Nested(QuakeMLRealQuantityType)
    bottomlatitude = fields.Nested(QuakeMLRealQuantityType)
    bottomdepth = fields.Nested(QuakeMLRealQuantityType)
    holediameter = fields.Nested(QuakeMLRealQuantityType)
    casingdiameter = fields.Nested(QuakeMLRealQuantityType)

    topclosed = fields.Boolean()
    bottomclosed = fields.Boolean()
    sectiontype = fields.String()
    casingtype = fields.String()
    description = fields.String()

    publicid = fields.String()

    hydraulics = fields.Nested(HydraulicSampleSchema, many=True)

    @post_load
    def postprocess(self, data):
        return self.make_object(self._transform(data))

    def make_object(self, data):
        if self.EContext.ORM in self.context:
            # XXX(damb): Wrap samples with Hydraulics enevelope
            if 'hydraulics' in data:
                data['hydraulics'] = Hydraulics(samples=data['hydraulics'])
            return WellSection(
                **self._flatten_object(data, self.__QUAKEML_TYPES))
        return data

    def _transform(self, data):

        transform_func = self._transform_callback
        if 'transform_callback' in self.context:
            transform_func = self.context['transform_callback']

        try:
            data['toplongitude']['value'], \
                data['toplatitude']['value'], \
                data['topdepth']['value'] = transform_func(
                data['toplongitude']['value'],
                data['toplatitude']['value'],
                data['topdepth']['value'])
            data['bottomlongitude']['value'], \
                data['bottomlatitude']['value'], \
                data['bottomdepth']['value'] = transform_func(
                data['bottomlongitude']['value'],
                data['bottomlatitude']['value'],
                data['bottomdepth']['value'])
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


class InjectionWellSchema(SchemaBase):
    """
    `Marshmallow <https://marshmallow.readthedocs.io/en/3.0/>`_ schema for an
    injection well.
    """
    publicid = fields.String()

    sections = fields.Nested(WellSectionSchema, many=True)

    @post_load
    def make_object(self, data):
        if self.EContext.ORM in self.context:
            return InjectionWell(**data)
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
    SRS_EPSG = 4326

    LOGGER = 'RAMSIS.io.hydwsboreholehydraulicsdeserializer'

    def __init__(self, **kwargs):
        """
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
        if isinstance(data, io.IOBase):
            data = data.read()

        # XXX(damb): Pass transformation rule/function by means of the
        # ma.Schema context
        crs_transform = self._transform_callback or self._transform
        ctx = {
            SchemaBase.EContext.ORM: True,
            'transform_callback': functools.partial(
                crs_transform, source_proj=self.SRS_EPSG,
                target_proj=self.proj)}
        return InjectionWellSchema(context=ctx).loads(data)


IOBase.register(HYDWSBoreholeHydraulicsDeserializer)
DeserializerBase.register(HYDWSBoreholeHydraulicsDeserializer)
