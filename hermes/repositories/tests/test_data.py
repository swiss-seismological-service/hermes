import json
import os
import uuid
from datetime import datetime

import pandas as pd
from hydws.parser import BoreholeHydraulics
from seismostats import Catalog
from sqlalchemy import text

from hermes.repositories.data import (InjectionObservationRepository,
                                      InjectionPlanRepository,
                                      SeismicityObservationRepository)
from hermes.repositories.project import (ForecastRepository,
                                         ForecastSeriesRepository)
from hermes.schemas.project_schemas import Forecast, ForecastSeries

MODULE_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'data')


class TestData:

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

    def test_create_injectionobservation(self, session, connection):
        forecast = Forecast(oid=uuid.uuid4(),
                            starttime=datetime(2021, 1, 1),
                            endtime=datetime(2021, 1, 2))

        forecast_oid = ForecastRepository.create(session, forecast).oid

        with open(os.path.join(MODULE_LOCATION, 'hydraulics.json'), 'rb') as f:
            [data] = json.load(f)

        injection_oid = InjectionObservationRepository.create_from_hydjson(
            session, json.dumps(data), forecast_oid)

        assert connection.execute(
            text(
                'SELECT COUNT(*) FROM injectionobservation WHERE oid = :oid'),
            {'oid': injection_oid}
        ).scalar() == 1

        InjectionObservationRepository.delete(session, injection_oid)

        borehole_hydraulics = BoreholeHydraulics(data)

        injection_oid = \
            InjectionObservationRepository.create_from_borehole_hydraulics(
                session, borehole_hydraulics, forecast_oid)

        assert connection.execute(
            text(
                'SELECT COUNT(*) FROM injectionobservation WHERE oid = :oid'),
            {'oid': injection_oid}
        ).scalar() == 1

    def test_create_injectionplan(self, session, connection):
        forecastseries = ForecastSeries(oid=uuid.uuid4(),
                                        name='test_series',)

        forecastseries_oid = ForecastSeriesRepository.create(
            session, forecastseries).oid

        with open(os.path.join(MODULE_LOCATION, 'hydraulics.json'), 'rb') as f:
            [data] = json.load(f)

        injectionplan_oid = InjectionPlanRepository.create_from_hydjson(
            session, json.dumps(data), 'test_plan', forecastseries_oid)

        assert connection.execute(
            text(
                'SELECT COUNT(*) FROM injectionplan WHERE oid = :oid'),
            {'oid': injectionplan_oid}
        ).scalar() == 1

        InjectionPlanRepository.delete(session, injectionplan_oid)

        borehole_hydraulics = BoreholeHydraulics(data)

        injectionplan_oid = \
            InjectionPlanRepository.create_from_borehole_hydraulics(
                session, borehole_hydraulics, 'test_plan', forecastseries_oid)

        assert connection.execute(
            text(
                'SELECT COUNT(*) FROM injectionplan WHERE oid = :oid'),
            {'oid': injectionplan_oid}
        ).scalar() == 1
