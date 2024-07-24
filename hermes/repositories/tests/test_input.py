import os
import uuid
from datetime import datetime

import pandas as pd
from seismostats import Catalog
from sqlalchemy import text

from hermes.repositories.forecast import ForecastRepository
from hermes.repositories.input import SeismicityObservationRepository
from hermes.schemas import Forecast

MODULE_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data')


class TestInput:

    def test_create_seismicityobservation(self, session, connection):
        forecast = Forecast(oid=uuid.uuid4(),
                            starttime=datetime(2021, 1, 1),
                            endtime=datetime(2021, 1, 2))

        forecast_oid = ForecastRepository.create(session, forecast).oid

        catalog_path = os.path.join(MODULE_LOCATION, 'catalog.parquet.gzip')

        catalog = Catalog(pd.read_parquet(catalog_path))

        seismicity_oid = SeismicityObservationRepository.create_from_catalog(
            session, catalog, forecast_oid)

        assert connection.execute(
            text(
                'SELECT COUNT(*) FROM seismicityobservation WHERE oid = :oid'),
            {'oid': seismicity_oid}
        ).scalar() == 1

        catalog_qml = catalog.to_quakeml()
        SeismicityObservationRepository.create_from_quakeml(
            session, catalog_qml, forecast_oid)
        assert connection.execute(
            text(
                'SELECT COUNT(*) FROM seismicityobservation')).scalar() == 2

        obs_db = SeismicityObservationRepository.get_by_id(
            session, seismicity_oid)

        assert obs_db.data.decode('utf-8')
