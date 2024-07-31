from datetime import datetime
from unittest.mock import MagicMock, patch

from hermes.flows.create_forecast import ForecastExecutor
from hermes.repositories.types import SessionType
from hermes.schemas import SeismicityObservation


# too many mocks, however this function binds together the whole flow
# of the forecast logic.
@patch('hermes.flows.create_forecast.get_catalog')
@patch('hermes.repositories.project.'
       'ForecastSeriesRepository.get_model_configs')
@patch('hermes.repositories.data.SeismicityObservationRepository.create')
@patch('hermes.repositories.project.ForecastRepository.create')
@patch('hermes.repositories.project.ProjectRepository.get_by_id')
class TestModels:
    def test_import(self,
                    mock_p_c, mock_f_c, mock_obs_c, mock_conf_g, mock_cat_c,
                    project, forecastseries, forecast, model_config):

        # mock all repository calls
        mock_ssn = MagicMock(spec=SessionType)
        mock_cat_c().to_quakeml.return_value = 'data'
        mock_p_c.return_value = project
        mock_f_c.return_value = forecast
        mock_obs_c.return_value = SeismicityObservation(data='data')
        mock_conf_g.return_value = [model_config]

        starttime = datetime(2021, 1, 2, 0, 30, 0)

        executor = ForecastExecutor(mock_ssn,
                                    forecastseries,
                                    starttime)

        assert executor.model_run_infos[0].config == model_config
        assert len(executor.model_run_infos) == 1

        forecast_arg = mock_f_c.call_args[0][1]
        assert forecast_arg.starttime == starttime
        assert forecast_arg.forecastseries_oid == forecastseries.oid
