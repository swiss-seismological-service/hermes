# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
Utilities for SFM-Worker data import/export.
"""
import xmltodict
import zipfile
from io import BytesIO
from marshmallow import (Schema, fields, pre_load,
                         post_load, EXCLUDE)
from osgeo import gdal

from ramsis.datamodel.hazard import HazardPointValue, HazardCurve, GeoPoint,\
    HazardMap
from RAMSIS.io.utils import (DeserializerBase, IOBase,
                             _IOError)

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


class BaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE


class ComboRenderer:
    @staticmethod
    def loads(s, *args, **kwargs):
        data = xmltodict.parse(s, force_list=True)
        return data


class HazardPointValueSchema(BaseSchema):
    poe = fields.Float(data_key='poE')
    groundmotion = fields.Float(data_key='iml')

    @pre_load
    def preload(self, data, **kwargs):
        self.context['geopoint'] = data['geopoint']
        return data

    @post_load
    def postload(self, data, **kwargs):
        data['hazardintensitytype'] = self.context['IMT']
        point_value = HazardPointValue(**data)
        point_value.geopoint = self.context['geopoint']
        return point_value


class HazardCurveSchema(BaseSchema):
    samples = fields.Nested(HazardPointValueSchema, data_key='poEs', many=True)

    @pre_load
    def alter_fields(self, data, **kwargs):
        """
        Before a hazard curve  is deserialized, move the location
        and intensity measure level into the data at the hazard point
        value level so that the object created is populated with this data.
        """
        session = self.context.get('session')
        lat, lon = (float(loc) for loc in data['gml:Point'][0]["gml:pos"][0].
                    split(" "))
        geopoint = session.query(GeoPoint).filter(
            GeoPoint.lat == lat,
            GeoPoint.lon == lon).\
            first()

        use_geopoint = geopoint if geopoint else GeoPoint(
            lat=lat, lon=lon)

        del data['gml:Point']
        poes_dict = [dict([('poE', float(poe))]) for poe in
                     data['poEs'][0].split(' ')]
        imls = self.context["IMLs"][0].split(' ')

        for poe_dict, iml in zip(poes_dict, imls):
            poe_dict['iml'] = iml
            poe_dict['geopoint'] = use_geopoint
        data['poEs'] = poes_dict
        return data

    @post_load
    def make_object(self, data, **kwargs):
        return HazardCurve(**data)


class HazardCurvesSchema(BaseSchema):
    hazardcurve = fields.Nested(HazardCurveSchema, data_key='hazardCurve',
                                many=True)

    @pre_load
    def preload(self, data, **kwargs):
        self.context["IMLs"] = data["IMLs"]
        self.context["IMT"] = data["@IMT"]
        return data

    @post_load
    def postload(self, data, **kwargs):
        return data

class HazardMapPointSchema(BaseSchema):
    lat = fields.Float(data_key='@lat')
    lon = fields.Float(data_key='@lon')
    groundmotion = fields.Float(data_key='@iml')

    @post_load
    def postload(self, data, **kwargs):
        session = self.context.get('session')
        geopoint = session.query(GeoPoint).filter(
            GeoPoint.lat == data["lat"],
            GeoPoint.lon == data["lon"]).\
            first()

        data["geopoint"] = geopoint if geopoint else GeoPoint(
            lat=data["lat"], lon=data["lon"])

        data["poe"] = self.context["poe"]
        data["hazardintensitytype"] = self.context["IMT"]
        del data['lat']
        del data['lon']
        return HazardPointValue(**data)


class HazardMapSchema(BaseSchema):
    samples = fields.Nested(HazardMapPointSchema, data_key='node', many=True)

    @pre_load
    def preload(self, data, **kwargs):
        self.context["poe"] = data["@poE"]
        self.context["IMT"] = data["@IMT"]
        return data

    @post_load
    def postload(self, data, **kwargs):
        return HazardMap(**data)

class NRMLSchema(BaseSchema):
    hazardcurves = fields.Nested(HazardCurvesSchema, data_key='hazardCurves',
                                 many=True)
    hazardmap = fields.Nested(HazardMapSchema, data_key='hazardMap',
                                 many=True)

    @pre_load
    def preload(self, data, **kwargs):
        return data


class HazardXMLSchema(BaseSchema):
    class Meta:
        render_module = ComboRenderer
        unknown = EXCLUDE
    nrml = fields.Nested(NRMLSchema, many=True)

    @pre_load
    def preload(self, data, **kwargs):
        return data


class OQHazardResultsListDeserializer():
    """
    Deserializes a list of results data  structure from
    hazard workers.
    """
    def _loado(self, data_list):
        """
        Load data from list of results from OpenQuake into
        known dict format.
        """
        query_urls = []
        # Response returns a list inside a list
        data = data_list[0]
        for output in data:
            if output['type'] in ['hcurves', 'hmaps']:
                assert 'xml' in output['outtypes']
                query_urls.append(
                    {'url': output['url'],
                     'type': output['type'],
                     'id': output['id'],
                     'name': output['name']})
        return query_urls


class OQHazardOMessageDeserializer(DeserializerBase):
    """
    Deserializes a result data structure which has been output from
    hazard workers.
    """
    def __init__(self, session, **kwargs):
        """
        :param bool many: Allow the deserialization of many arguments
        """
        self.session = session
        self._many = kwargs.get('many', False)
        self._partial = kwargs.get('partial', False)
        self._context = {'session': session}

    @property
    def _ctx(self):
        return self._context

    def _deserialize(self, data, output_type):
        # sarsonl NotImplemented
        pass

    def _read_ziparchive(self, archive):
        with BytesIO(archive) as zip_obj:
            read_obj = zipfile.ZipFile(zip_obj)
            infolist = read_obj.infolist()
            for zipinfo_obj in infolist:
                obj_filename = zipinfo_obj.filename
                yield read_obj.read(obj_filename).decode()

    def _loado(self, data, **kwargs):
        """
        Deserializes a data structure returned by Hazard-Worker
        implementations.
        """
        ziparchive_gen = self._read_ziparchive(data[0].content)
        output_type = kwargs.get('output_type')
        hazard_curves = []
        hazard_maps = []
        if output_type == 'hcurves':
            for hcurve_data in ziparchive_gen:
                nrml = HazardXMLSchema(
                    context=self._ctx, many=False,
                    partial=self._partial).loads(hcurve_data)
                for ind_nrml in nrml['nrml']:
                    for haz_curves in ind_nrml['hazardcurves']:
                        hazard_curves.append(haz_curves)
        elif output_type == 'hmaps':
            for hmap_data in ziparchive_gen:
                nrml = HazardXMLSchema(
                    context=self._ctx, many=False,
                    partial=self._partial).loads(hmap_data)
                haz_map = nrml['nrml']
                hazard_maps.extend(nrml['nrml'])
        return {'hazard_curves': hazard_curves, 'hazard_maps': hazard_maps}


IOBase.register(OQHazardResultsListDeserializer)
DeserializerBase.register(OQHazardResultsListDeserializer)
IOBase.register(OQHazardOMessageDeserializer)
DeserializerBase.register(OQHazardOMessageDeserializer)
