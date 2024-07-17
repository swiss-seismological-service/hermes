import uuid
from datetime import datetime

import pytest
from shapely import Polygon
from sqlalchemy.exc import IntegrityError

from hermes.repositories.forecast import ForecastRepository
from hermes.repositories.forecastseries import ForecastSeriesRepository
from hermes.repositories.modelrun import ModelRunRepository
from hermes.repositories.results import (GridCellRepository,
                                         ModelResultRepository,
                                         TimeStepRepository)
from hermes.schemas import (Forecast, ForecastSeries, GridCell, ModelResult,
                            ModelRun, TimeStep)
from hermes.schemas.base import EResultType


class TestGridCells:
    def test_create(self, session, forecastseries):
        cell1 = GridCell(geom=Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                         depth_max=10,
                         depth_min=5,
                         forecastseries_oid=forecastseries.oid)
        cell1 = GridCellRepository.create(session, cell1)
        assert cell1.oid is not None

    def test_get_by_id(self, session, forecastseries):
        cell1 = GridCell(geom=Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                         depth_max=10,
                         depth_min=5,
                         forecastseries_oid=forecastseries.oid)
        cell1 = GridCellRepository.create(session, cell1)

        cell2 = GridCellRepository.get_by_id(session, cell1.oid)
        assert cell1 == cell2

    def test_unique_constraint(self, session, forecastseries):
        fs = ForecastSeries(oid=uuid.uuid4(),
                            name='test',
                            forecast_starttime=datetime(2021, 1, 1))

        poly1 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        poly2 = Polygon([(0, 0), (2, 0), (1, 1), (0, 1)])

        cell1 = GridCell(geom=poly1,
                         depth_max=10,
                         depth_min=5,
                         forecastseries_oid=forecastseries.oid)

        cell2 = cell1.model_copy(update={'geom': poly2})
        cell3 = cell1.model_copy(update={'depth_max': 20})
        cell4 = cell1.model_copy(update={'depth_min': 2})
        cell5 = cell1.model_copy(update={'forecastseries_oid': fs.oid})

        ForecastSeriesRepository.create(session, fs)
        GridCellRepository.create(session, cell1)
        GridCellRepository.create(session, cell2)
        GridCellRepository.create(session, cell3)
        GridCellRepository.create(session, cell4)
        GridCellRepository.create(session, cell5)

        with pytest.raises(IntegrityError):
            GridCellRepository.create(session, cell1)


class TestTimeStep:
    def test_create(self, session, forecastseries):
        timestep = TimeStep(starttime=datetime(2021, 1, 1),
                            endtime=datetime(2021, 1, 2),
                            forecastseries_oid=forecastseries.oid)
        timestep = TimeStepRepository.create(session, timestep)
        assert timestep.oid is not None

    def test_get_by_id(self, session, forecastseries):
        timestep = TimeStep(starttime=datetime(2021, 1, 1),
                            endtime=datetime(2021, 1, 2),
                            forecastseries_oid=forecastseries.oid)
        timestep = TimeStepRepository.create(session, timestep)

        timestep2 = TimeStepRepository.get_by_id(session, timestep.oid)
        assert timestep == timestep2

    def test_unique_constraint(self, session, forecastseries):
        fs = ForecastSeries(oid=uuid.uuid4(),
                            name='test',
                            forecast_starttime=datetime(2021, 1, 1))

        ts1 = TimeStep(starttime=datetime(2021, 1, 1),
                       endtime=datetime(2021, 1, 2),
                       forecastseries_oid=forecastseries.oid)

        ts2 = ts1.model_copy(update={'starttime': datetime(2021, 1, 3)})
        ts3 = ts1.model_copy(update={'endtime': datetime(2021, 1, 3)})
        ts4 = ts1.model_copy(update={'forecastseries_oid': fs.oid})

        ForecastSeriesRepository.create(session, fs)
        TimeStepRepository.create(session, ts1)
        TimeStepRepository.create(session, ts2)
        TimeStepRepository.create(session, ts3)
        TimeStepRepository.create(session, ts4)

        with pytest.raises(IntegrityError):
            TimeStepRepository.create(session, ts1)


class TestModelResult:

    @pytest.fixture(autouse=True)
    def _create_step_cell(self, session):

        forecastseries = ForecastSeries(
            oid=uuid.uuid4(),
            name='test',
            forecast_starttime=datetime(2021, 1, 1))
        self.forecastseries_oid = ForecastSeriesRepository.create(
            session, forecastseries).oid

        forecast = Forecast(oid=uuid.uuid4(),
                            starttime=datetime(2021, 1, 1),
                            endtime=datetime(2021, 1, 2),
                            forecastseries_oid=self.forecastseries_oid)
        self.forecast_oid = ForecastRepository.create(session, forecast).oid

        modelrun = ModelRun(oid=uuid.uuid4(),
                            forecast_oid=self.forecast_oid)
        self.modelrun_oid = ModelRunRepository.create(session, modelrun).oid

        cell = GridCell(geom=Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                        depth_max=10,
                        depth_min=5,
                        forecastseries_oid=self.forecastseries_oid)
        self.cell = GridCellRepository.create(session, cell)

        timestep = TimeStep(starttime=datetime(2021, 1, 1),
                            endtime=datetime(2021, 1, 2),
                            forecastseries_oid=self.forecastseries_oid)
        self.timestep = TimeStepRepository.create(session, timestep)

        modelresult = ModelResult(result_type=EResultType.CATALOG,
                                  timestep_oid=self.timestep.oid,
                                  gridcell_oid=self.cell.oid,
                                  modelrun_oid=self.modelrun_oid)
        self.modelresult_oid = ModelResultRepository.create(
            session, modelresult).oid

    def test_delete_cascade(self, session):

        ModelResultRepository.delete(session, self.modelresult_oid)
        assert ModelResultRepository.get_by_id(
            session, self.modelresult_oid) is None
        assert GridCellRepository.get_by_id(session, self.cell.oid) is not None
        assert TimeStepRepository.get_by_id(
            session, self.timestep.oid) is not None

        ForecastSeriesRepository.delete(session, self.forecastseries_oid)
        assert GridCellRepository.get_by_id(session, self.cell.oid) is None
        assert TimeStepRepository.get_by_id(session, self.timestep.oid) is None
