from marshmallow import Schema, fields, post_load

from forecast import Forecast, ForecastInput, Scenario, ForecastResult,\
    ModelResult, RatePrediction
from seismics import SeismicCatalog, SeismicEvent
from hydraulics import InjectionPlan, InjectionHistory, InjectionSample


class RatePredictionSchema(Schema):
    rate = fields.Float()
    b_val = fields.Float()
    prob = fields.Float()
    score = fields.Float()

    @post_load
    def make_rate_prediction(self, data):
        return RatePrediction(**data)


class ModelResultSchema(Schema):
    model_name = fields.Str()
    failed = fields.Boolean()
    failure_reason = fields.Str()
    rate_prediction = fields.Nested(RatePredictionSchema)

    @post_load
    def make_model_result(self, data):
        model_result = ModelResult()
        for key in data:
            setattr(model_result, key, data[key])
        return model_result


class ForecastResultSchema(Schema):
    hazard_oq_calc_id = fields.Integer()
    risk_oq_calc_id = fields.Integer()
    model_results = fields.Nested(ModelResultSchema)

    @post_load
    def make_forecast_result(self, data):
        forecast_result = ForecastResult()
        for key in data:
            setattr(forecast_result, key, data[key])
        return forecast_result


class InjectionSamplesSchema(Schema):
    date_time = fields.DateTime()
    flow_dh = fields.Float()
    flow_xt = fields.Float()
    pr_dh = fields.Float()
    pr_xt = fields.Float()

    @post_load
    def make_injection_sample(self, data):
        return InjectionSample(**data)


class InjectionHistorySchema(Schema):
    samples = fields.Nested(InjectionSamplesSchema)

    @post_load
    def make_injection_history(self, data):
        injection_history = InjectionHistory(store=None)
        for key in data:
            setattr(injection_history, key, data[key])
        return injection_history


class InjectionPlanSchema(Schema):
    samples = fields.Nested(InjectionSamplesSchema)

    @post_load
    def make_injection_plan(self, data):
        injection_plan = InjectionPlan()
        for key in data:
            setattr(injection_plan, key, data[key])
        return injection_plan


class ScenarioSchema(Schema):
    injection_plans = fields.Nested(InjectionPlanSchema)

    @post_load
    def make_scenario(self, data):
        scenario = Scenario()
        for key in data:
            setattr(scenario, key, data[key])
        return scenario


class SeismicEventSchema(Schema):
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


class SeismicCatalogSchema(Schema):
    catalog_date = fields.DateTime()
    seismic_events = fields.Nested(SeismicEventSchema)

    @post_load
    def make_seismic_catalog(self, data):
        seismic_catalog = SeismicCatalog(store=None)
        for key in data:
            setattr(seismic_catalog, key, data[key])
        return seismic_catalog


class ForecastInputSchema(Schema):
    input_catalog = fields.Nested(SeismicCatalogSchema)
    scenarios = fields.Nested(ScenarioSchema)

    @post_load
    def make_forecast_input(self, data):
        forecast_input = ForecastInput()
        for key in data:
            setattr(forecast_input, key, data[key])
        return forecast_input


class ForecastSchema(Schema):
    name = fields.Str()
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
