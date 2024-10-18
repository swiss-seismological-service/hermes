import os
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import text

from hermes.flows import forecast_runner

MODULE_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data')


class TestDefaultModelRun:

    @patch('hermes.flows.forecast_builder.get_catalog')
    @patch('hermes.flows.forecast_builder.Session')
    @patch('hermes.flows.modelrun_handler.Session')
    def test_full_flow(self,
                       mock_session_m, mock_session_fc, mock_get_catalog,
                       session, forecastseries, model_config,
                       prefect):

        with open(MODULE_LOCATION + '/catalog.xml', 'r') as f:
            catalog = f.read()

        mock_session_fc.return_value = session
        mock_session_m.return_value = session
        mock_get_catalog().to_quakeml.return_value = catalog

        forecast_runner(forecastseries.oid,
                        starttime=datetime(2022, 1, 1, 0, 0, 0))

        n_modelresult = session.execute(
            text('SELECT COUNT(*) FROM modelresult'))
        assert n_modelresult.scalar() == 100

        n_seismicevents = session.execute(
            text('SELECT COUNT(*) FROM seismicevent'))
        assert n_seismicevents.scalar() == 344
