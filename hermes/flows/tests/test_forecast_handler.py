from unittest.mock import ANY, MagicMock, patch

from hermes.flows.forecast_handler import forecast_runner
from hermes.schemas import SeismicityObservation
from hermes.schemas.project_schemas import Forecast


@patch('hermes.repositories.project.ForecastRepository.update_status',
       autocast=True)
@patch('hermes.flows.forecast_handler.default_model_runner', autocast=True)
@patch('hermes.repositories.data.'
       'SeismicityObservationRepository.create_from_quakeml',
       autocast=True,
       return_value=SeismicityObservation(data='data'))
@patch('hermes.io.SeismicityDataSource.from_uri',
       autocast=True)
@patch('hermes.repositories.project.ForecastRepository.create',
       autocast=True)
@patch('hermes.repositories.project.'
       'ForecastSeriesRepository.get_model_configs',
       autocast=True)
@patch('hermes.repositories.project.ForecastSeriesRepository.get_by_id',
       autocast=True)
@patch('hermes.flows.forecast_handler.Session')
class TestForecastHandler:
    def test_full(self,
                  session,
                  mock_fs_get_by_id,
                  mock_fs_get_model_configs,
                  mock_f_create: MagicMock,
                  mock_get_catalog,
                  mock_so_create,
                  mock_default_model_runner: MagicMock,
                  mock_update_status: MagicMock,
                  forecastseries,
                  forecast,
                  model_config,
                  prefect):

        mock_f_create.return_value = forecast
        mock_fs_get_by_id.return_value = forecastseries
        mock_fs_get_model_configs.return_value = [model_config]

        mock_get_catalog().get_quakeml.return_value = 'data'

        forecast_handler = forecast_runner(forecastseries.oid,
                                           forecastseries.schedule_starttime)

        # make sure times can be compared and don't have incompatible tzinfo
        assert forecast_handler.starttime < forecast_handler.endtime
        assert forecastseries.observation_starttime < \
            forecast_handler.starttime

        mock_f_create.assert_called_with(ANY, Forecast(
            forecastseries_oid=forecastseries.oid,
            status='PENDING',
            starttime=forecast_handler.starttime,
            endtime=forecast_handler.endtime
        ))

        assert len(mock_default_model_runner.call_args_list) == 1
