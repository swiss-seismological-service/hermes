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

#from openquake.baselib.node import node_from_xml, read_nodes
from marshmallow import Schema, fields, pre_load, EXCLUDE
from ramsis.datamodel.hazard import HazardPointValue, HazardCurve, GeoPoint
import xmltodict

class BaseSchema(Schema):
    class Meta:
        unknown=EXCLUDE

class ComboRenderer:
    @staticmethod
    def loads(s, *args, **kwargs):
        data = xmltodict.parse(s.read(), force_list=True)
        return data

class HazardPointValueSchema(BaseSchema):
    poe = fields.Float(data_key='poE')
    groundmotion = fields.Float(data_key='iml')
    @pre_load
    def preload(self, data, **kwargs):
        return data

class GMLPointSchema(BaseSchema):
    lat = fields.Float()
    lon = fields.Float()
    @pre_load
    def translate_points(self, data, **kwargs):
        # convert to local coords
        print("gml data", data)
        lat, lon = (float(loc) for loc in data["gml:pos"][0].split(" "))
        return {"lat": lat, "lon": lon}

class HazardCurveSchema(BaseSchema):
    gml_point = fields.Nested(GMLPointSchema, data_key='gml:Point', many=True)
    samples = fields.Nested(HazardPointValueSchema, data_key='poEs', many=True)
    @pre_load
    def alter_fields(self, data, **kwargs):
        poes_dict = [dict([('poE', float(poe))]) for poe in data['poEs'][0].split(' ')]
        imls = self.context["IMLs"][0].split(' ')
        for poe_dict, iml in zip(poes_dict, imls):
            poe_dict['iml'] = iml
        data['poEs'] = poes_dict
        return data
    #@post_load
    #def make_object(self, data, **kwargs):
    #    return HazardCurve(**data)
        

class HazardCurvesSchema(BaseSchema):
    hazardcurve = fields.Nested(HazardCurveSchema, data_key='hazardCurve', many=True)
    @pre_load
    def preload(self, data, **kwargs):
        iml = data["IMLs"]
        self.context["IMLs"] = iml
        return data


class NRMLSchema(BaseSchema):
    hazardcurves = fields.Nested(HazardCurvesSchema, data_key='hazardCurves', many=True)

class HazardXMLSchema(BaseSchema):
    class Meta:
        render_module = ComboRenderer
        unknown=EXCLUDE
    nrml = fields.Nested(NRMLSchema, many=True)

    @pre_load
    def preload(self, data, **kwargs):
        print(data)
        return data

def get_geopoint(gml_point):
    geopoint = session.query(GeoPoint).filter(
        GeoPoint.lat == gml_point['lat'],
        GeoPoint.lon == gml_point['lon']).\
        one_or_none()
    return geopoint

def create_hazard_curve_object(hazard_curve, session):
    # There is known to be a single geo point associated with each curve
    # Check if geo point already exists
    gml_point = hazard_curve['gml_point'][0]
    geopoint = get_geopoint(gml_point)
    geopoint_exists = True if geopoint else False
    if not geopoint_exists:
         geopoint = GeoPoint(**gml_point)

    del hazard_curve['gml_point']
    hazardcurve = HazardCurve(**hazard_curve)
    geopoint.hazardpointvalues.append(hazardcurve.samples)
    return hazard_curve, geopoint, geopoint_exists

class _OQHazardCurveSchema(_SchemaBase):
    data = fields.Method("_serialize_data", deserialize="_deserialize_data")

    #@post_dump
    #def clear_missing(self, data, **kwargs):
    #    return self._clear_missing(data)

    #def _serialize_data(self, obj):
    #    if 'data' in obj:
    #        if isinstance(obj['data'], list):
    #            return SFMWorkerResponseDataSchema(
    #                context=self.context, many=True).dump(obj['data'])

    #        return SFMWorkerResponseDataSchema(
    #            context=self.context).dump(obj['data'])

    def _deserialize_data(self, value):
        if isinstance(value, list):
            return SFMWorkerResponseDataSchema(
                context=self.context, many=True).load(value)

        return SFMWorkerResponseDataSchema(context=self.context).load(value)


class OQHazardResultsListDeserializer():

    def _deserialize(self, data):
        query_urls = []
        for output in data:
            if output['type'] in ['hcurves', 'hmaps']:
                assert 'xml' in output['outtypes']
                query_urls.append(
                    {'url': output['url'],
                     'type': output['type']
                     'id': output['id'],
                     'name': output['name']})
        return query_urls


class OQHazardOMessageDeserializer(DeserializerBase):
    """
    Serializes a data structure which later can be consumed by SFM workers.
    """
    def __init__(self, session, **kwargs):
        """
        :param bool many: Allow the deserialization of many arguments
        """
        super().__init__(**kwargs)

        self._context = {'session': session}

    def _deserialize(self, data, output_type):
        """
        Deserializes a data structure returned by SFM-Worker implementations.
        """
        if output_type == 'hazardcurve':
            return _OQHazardCurveMessageSchema(
                context=self._context, many=self._many).loads(data)

    def _loado(self, data):
        return _OQHazardCurveMessageSchema(
            context=self._context, many=self._many,
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
