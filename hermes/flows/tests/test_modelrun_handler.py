import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call, patch

import numpy as np
from shapely import Polygon

from hermes.flows.modelrun_handler import DefaultModelRunHandler
from hermes.schemas import DBModelRunInfo, ModelConfig
from hermes.schemas.base import EStatus

MODULE_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data')


def mock_function(results):
    return MagicMock()


class TestModelRunner:
    @patch('hermes.flows.modelrun_handler.DefaultModelRunHandler'
           '._save_catalog', autocast=True)
    @patch('hermes.flows.modelrun_handler.ModelRunRepository'
           '.update_status', autocast=True)
    @patch('hermes.flows.modelrun_handler.ModelRunRepository'
           '.create', autocast=True)
    @patch('hermes.flows.tests.test_modelrun_handler.mock_function',
           autocast=True)
    def test_run(self,
                 # MOCKS
                 mock_model_call: MagicMock,
                 mock_modelrun_repo_create: MagicMock,
                 mock_modelrun_repo_update_status: MagicMock,
                 mock_handler_catalog_save: MagicMock,
                 # FIXTURES
                 modelconfig_db: ModelConfig,
                 prefect
                 ):

        modelrun_info = DBModelRunInfo(
            forecast_start=datetime(2022, 1, 1),
            forecast_end=datetime(2022, 1, 1) + timedelta(days=30),
            bounding_polygon=Polygon(
                np.load(os.path.join(MODULE_LOCATION, 'ch_rect.npy'))),
            depth_min=0,
            depth_max=1)

        mock_model_call.return_value = "teststring"

        handler = DefaultModelRunHandler(modelrun_info, modelconfig_db)
        handler.run()

        assert call(handler.model_input.model_dump()) == \
            mock_model_call.call_args_list[0]

        mock_handler_catalog_save.assert_called_with("teststring")
        assert mock_modelrun_repo_update_status.call_args_list[0][0][-1] \
            == EStatus.COMPLETED
