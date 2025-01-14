from hermes.flows.modelrun_builder import ModelRunBuilder


class TestModelRunBuilder:
    def test_build_runs(self,
                        # FIXTURES
                        forecast,
                        forecastseries_db,
                        modelconfig_db
                        ):

        builder = ModelRunBuilder(
            forecast, forecastseries_db, [modelconfig_db])
        assert len(builder.runs) == 1
        assert builder.runs[0][1] == modelconfig_db

        modelrun_info = builder.runs[0][0]
        assert modelrun_info.forecastseries_oid == forecastseries_db.oid
        assert modelrun_info.forecast_oid == forecast.oid
        assert modelrun_info.forecast_start == forecast.starttime
        assert modelrun_info.forecast_end == forecast.endtime
        assert modelrun_info.bounding_polygon == \
            forecastseries_db.bounding_polygon.wkt
        assert modelrun_info.depth_min == forecastseries_db.depth_min
        assert modelrun_info.depth_max == forecastseries_db.depth_max
        assert modelrun_info.injection_plan_oid is None
        assert modelrun_info.injection_observation_oid is None
        assert modelrun_info.seismicity_observation_oid is None
