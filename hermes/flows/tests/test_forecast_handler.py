import os
from datetime import datetime
from unittest.mock import MagicMock, patch

from prefect import flow

from hermes.flows.forecast_handler import (ForecastHandler, InjectionPlan,
                                           ModelConfig)
from hermes.schemas import ForecastSeries

MODULE_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data')
with open(os.path.join(MODULE_LOCATION, 'injection.json')) as f:
    INJECTION = f.read()
with open(os.path.join(MODULE_LOCATION, 'quakeml.xml')) as f:
    SEISMICITY = f.read()


@patch('hermes.flows.forecast_handler.default_model_runner',
       autocast=True)
@patch('hermes.io.SeismicityDataSource.from_uri',
       autocast=True)
@patch('hermes.io.HydraulicsDataSource.from_uri',
       autocast=True)
@patch('hermes.flows.forecast_handler.Session')
class TestForecastHandler:
    @flow
    def test_full(self,
                  # MOCKS
                  forecast_handler_session: MagicMock,
                  mock_get_injection: MagicMock,
                  mock_get_catalog: MagicMock,
                  mock_default_model_runner: MagicMock,
                  # FIXTURES
                  session,
                  forecastseries_db: ForecastSeries,
                  modelconfig_db: ModelConfig,
                  injectionplan_db: InjectionPlan,
                  prefect
                  ):
        forecast_handler_session.return_value.__enter__.return_value = session
        mock_get_catalog().get_quakeml.return_value = SEISMICITY
        mock_get_injection().get_json.return_value = INJECTION

        forecast_handler = ForecastHandler(
            forecastseries_db.oid,
            starttime=datetime(2022, 4, 21, 14, 50, 0),
            endtime=datetime(2022, 4, 21, 14, 55, 0)
        )
        forecast_handler.run()

        assert mock_default_model_runner.call_count == 1
        assert len(forecast_handler.forecastseries.injection_plans) == 1
        assert len(forecast_handler.modelconfigs) == 1
