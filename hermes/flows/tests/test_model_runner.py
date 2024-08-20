from unittest.mock import patch

from hermes.flows.model_runner import DefaultModelRunHandler


class TestModelRunner:
    @patch('hermes.flows.model_runner.DefaultModelRunHandler'
           '._fetch_seismicity_observation')
    def test_run(self,
                 mock_obs_get,
                 modelrun_info,
                 modelconfig,
                 seismicity_observation):

        mock_obs_get.return_value = seismicity_observation.data

        # handler = DefaultModelRunHandler(modelrun_info, modelconfig)
        # handler.run()
