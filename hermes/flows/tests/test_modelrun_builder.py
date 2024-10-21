from hermes.flows.modelrun_builder import ModelRunBuilder


class TestModelRunBuilder:
    def test_build_runs(self, forecast, forecastseries, model_config):
        builder = ModelRunBuilder(forecast, forecastseries, [model_config])
        assert len(builder.runs) == 1
        assert builder.runs[0][1] == model_config

        modelrun_info = builder.runs[0][0]
        assert modelrun_info.forecastseries_oid == forecastseries.oid
        assert modelrun_info.forecast_oid == forecast.oid
        assert modelrun_info.forecast_start == forecast.starttime
        assert modelrun_info.forecast_end == forecast.endtime
        assert modelrun_info.bounding_polygon == \
            forecastseries.bounding_polygon.wkt
        assert modelrun_info.depth_min == forecastseries.depth_min
        assert modelrun_info.depth_max == forecastseries.depth_max
        assert modelrun_info.injection_plan_oid is None
        assert modelrun_info.injection_observation_oid is None
        assert modelrun_info.seismicity_observation_oid is None
