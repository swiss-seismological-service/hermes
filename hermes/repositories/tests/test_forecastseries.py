import json
import os

from shapely.geometry import Polygon
from sqlalchemy import text

from hermes.repositories.forecastseries import ForecastSeriesRepository
from hermes.repositories.project import ProjectRepository
from hermes.repositories.tests.conftest import MODULE_LOCATION
from hermes.schemas.forecastseries import ForecastSeries


class TestForecastseries:

    def test_create(self, connection, session, project):
        with open(os.path.join(MODULE_LOCATION, 'forecastseries.json')) as f:
            forecastseries = ForecastSeries(
                name='forecastseries',
                project_oid=project.oid,
                **json.load(f))

        forecastseries = ForecastSeriesRepository.create(
            session, forecastseries)

        assert forecastseries.oid is not None
        assert 'FORGE' in forecastseries.tags

        tags = connection.execute(
            text('SELECT * FROM tag'))
        tags = [t.name for t in tags.all()]
        assert len(tags) == 2
        assert "INDUCED" in tags

        assert isinstance(forecastseries.bounding_polygon, Polygon)

    def test_delete(self, session, forecastseries):
        ProjectRepository.delete(session, forecastseries.project_oid)

        assert ForecastSeriesRepository.get_by_id(
            session, forecastseries.oid) is None
