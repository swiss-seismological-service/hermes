from marshmallow import Schema, fields, post_load

from forecast import ForecastSet, Forecast, ForecastInput, Scenario,\
    ForecastResult, ModelResult, RatePrediction
from seismics import SeismicCatalog, SeismicEvent
from hydraulics import InjectionPlan, InjectionHistory, InjectionSample
from skilltest import SkillTest
from project import Project
from injectionwell import InjectionWell, WellSection


class BaseSchema(Schema):
    def __init__(self, strict=True, **kwargs):
        super(BaseSchema, self).__init__(strict=strict, **kwargs)


class WellSectionSchema(BaseSchema):
    cased = fields.Boolean()

    @post_load
    def make_well_section(self, data):
        well_section = WellSection()
        for key in data:
            setattr(well_section, key, data[key])
        return well_section


class InjectionWellSchema(BaseSchema):
    sections = fields.Nested(WellSectionSchema)

    @post_load
    def make_injection_well(self, data):
        injection_well = InjectionWell(None, None, None)
        for key in data:
            setattr(injection_well, key, data[key])
        return injection_well


class SeismicEventSchema(BaseSchema):
    public_id = fields.Str()
    public_origin_id = fields.Str()
    public_magnitude_id = fields.Str()
    date_time = fields.DateTime()
    lat = fields.Float()
    lon = fields.Float()
    depth = fields.Float()
    x = fields.Float()
    y = fields.Float()
    z = fields.Float()
    magnitude = fields.Float()

    @post_load
    def make_seismic_event(self, data):
        params = ('date_time', 'magnitude', 'location')
        init = dict((k, data[k]) for k in params)
        rest = dict((k, data[k]) for k in data if k not in params)
        seismic_event = SeismicEvent(**init)
        for key in rest:
            setattr(seismic_event, key, rest[key])
        return seismic_event


class SeismicCatalogSchema(BaseSchema):
    catalog_date = fields.DateTime()
    seismic_events = fields.Nested(SeismicEventSchema, many=True)

    @post_load
    def make_seismic_catalog(self, data):
        seismic_catalog = SeismicCatalog(store=None)
        for key in data:
            setattr(seismic_catalog, key, data[key])
        return seismic_catalog


class InjectionSamplesSchema(BaseSchema):
    date_time = fields.DateTime()
    flow_dh = fields.Float(allow_none=True)
    flow_xt = fields.Float(allow_none=True)
    pr_dh = fields.Float(allow_none=True)
    pr_xt = fields.Float(allow_none=True)

    @post_load
    def make_injection_sample(self, data):
        return InjectionSample(**data)


class InjectionHistorySchema(BaseSchema):
    samples = fields.Nested(InjectionSamplesSchema)

    @post_load
    def make_injection_history(self, data):
        injection_history = InjectionHistory(store=None)
        for key in data:
            setattr(injection_history, key, data[key])
        return injection_history


class SkillTestSchema(BaseSchema):
    skill_score = fields.Float()
    test_interval = fields.Float()
    spatial_extent = fields.Float()
    reference_catalog = fields.Nested(SeismicCatalogSchema)

    @post_load
    def make_skill_test(self, data):
        skill_test = SkillTest()
        for key in data:
            setattr(skill_test, key, data[key])
        return skill_test


class RatePredictionSchema(BaseSchema):
    rate = fields.Float()
    b_val = fields.Float()
    prob = fields.Float()
    score = fields.Float()

    @post_load
    def make_rate_prediction(self, data):
        return RatePrediction(**data)


class ModelResultSchema(BaseSchema):
    model_name = fields.Str()
    failed = fields.Boolean()
    failure_reason = fields.Str()
    skill_test = fields.Nested(SkillTestSchema, allow_none=True)
    rate_prediction = fields.Nested(RatePredictionSchema, allow_none=True)

    @post_load
    def make_model_result(self, data):
        model_result = ModelResult()
        for key in data:
            setattr(model_result, key, data[key])
        return model_result


class ForecastResultSchema(BaseSchema):
    hazard_oq_calc_id = fields.Integer()
    risk_oq_calc_id = fields.Integer()
    model_results = fields.Nested(ModelResultSchema)

    @post_load
    def make_forecast_result(self, data):
        forecast_result = ForecastResult()
        for key in data:
            setattr(forecast_result, key, data[key])
        return forecast_result


class InjectionPlanSchema(BaseSchema):
    samples = fields.Nested(InjectionSamplesSchema, many=True)

    @post_load
    def make_injection_plan(self, data):
        injection_plan = InjectionPlan()
        for key in data:
            setattr(injection_plan, key, data[key])
        return injection_plan


class ScenarioSchema(BaseSchema):
    injection_plans = fields.Nested(InjectionPlanSchema, many=True)

    @post_load
    def make_scenario(self, data):
        scenario = Scenario()
        for key in data:
            setattr(scenario, key, data[key])
        return scenario


class ForecastInputSchema(BaseSchema):
    input_catalog = fields.Nested(SeismicCatalogSchema, allow_none=True)
    scenarios = fields.Nested(ScenarioSchema, many=True)

    @post_load
    def make_forecast_input(self, data):
        forecast_input = ForecastInput()
        for key in data:
            setattr(forecast_input, key, data[key])
        return forecast_input


class ForecastSchema(BaseSchema):
    name = fields.Str(allow_none=True)
    forecast_time = fields.DateTime()
    forecast_interval = fields.Float()
    mc = fields.Float()
    m_min = fields.Integer()
    m_max = fields.Integer()
    input = fields.Nested(ForecastInputSchema)

    @post_load
    def make_forecast(self, data):
        forecast = Forecast()
        for key in data:
            setattr(forecast, key, data[key])
        return forecast


class ForecastSetSchema(BaseSchema):
    forecasts = fields.Nested(ForecastSchema)

    @post_load
    def make_forecast_set(self, data):
        forecast_set = ForecastSet(store=None)
        for key in data:
            setattr(forecast_set, key, data[key])
        return forecast_set


class ProjectSchema(BaseSchema):
    title = fields.Str()
    injection_well = fields.Nested(InjectionWellSchema)
    injection_history = fields.Nested(InjectionHistorySchema)
    forecast_set = fields.Nested(ForecastSetSchema)
    seismic_catalog = fields.Nested(SeismicCatalogSchema)

    @post_load
    def make_project(self, data):
        project = Project(store=None)
        for key in data:
            setattr(project, key, data[key])
        return project
