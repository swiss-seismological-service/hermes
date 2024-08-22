from unittest.mock import MagicMock, call, patch

from hermes.flows.modelrun_handler import DefaultModelRunHandler
from hermes.schemas import DBModelRunInfo, ModelConfig


def mock_function(results):
    return MagicMock()


class TestModelRunner:
    @patch('hermes.flows.modelrun_handler.DefaultModelRunHandler'
           '._save_catalog', autocast=True)
    @patch('hermes.flows.modelrun_handler.ModelRunRepository'
           '.create', autocast=True)
    @patch('hermes.flows.tests.test_model_runner.mock_function',
           autocast=True)
    def test_run(self,
                 mock_model_call: MagicMock,
                 mock_modelrun_repo_create: MagicMock,
                 mock_handler_catalog_save: MagicMock,
                 modelrun_info: DBModelRunInfo,
                 modelconfig: ModelConfig,
                 ):

        mock_model_call.return_value = "teststring"

        handler = DefaultModelRunHandler(modelrun_info, modelconfig)
        handler.run()

        assert call(handler.model_input.model_dump()) == \
            mock_model_call.call_args_list[0]

        mock_handler_catalog_save.assert_called_with("teststring")
