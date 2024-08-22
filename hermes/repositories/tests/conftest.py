from datetime import datetime

import pytest
from shapely import Polygon
from sqlalchemy import Connection, event, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import scoped_session, sessionmaker

from config import get_settings
from hermes.datamodel.base import ORMBase
from hermes.repositories.database import create_engine, create_extensions
from hermes.repositories.project import (ForecastRepository,
                                         ForecastSeriesRepository,
                                         ModelConfigRepository,
                                         ProjectRepository)
from hermes.schemas import (EInput, EResultType, EStatus, Forecast,
                            ForecastSeries, ModelConfig, Project)

settings = get_settings()


def delete_database(connection: Connection, db_name: str):
    connection.execute(text("ROLLBACK"))
    try:
        connection.execute(text(f"DROP DATABASE {db_name}"))
    except ProgrammingError:
        # Probably the database does not exist, as it should be.
        connection.execute(text("ROLLBACK"))
    except OperationalError:
        print(
            "Could not drop database because it’s "
            "being accessed by other users (psql prompt open?)")
        connection.execute(text("ROLLBACK"))


@pytest.fixture(scope="class")
def connection(request: pytest.FixtureRequest) -> object:
    test_db_name = f"{settings.POSTGRES_DB}_test"

    url = URL.create(
        drivername='postgresql+psycopg2',
        username=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT
    )

    engine = create_engine(url)

    with engine.connect() as connection:
        connection.execution_options(isolation_level="AUTOCOMMIT")

        delete_database(connection, test_db_name)

        connection.execute(text(
            f"CREATE DATABASE {test_db_name};"
        ))

    engine = create_engine(
        f"{url.render_as_string(False)}/{test_db_name}"
    )
    create_extensions(engine)
    connection = engine.connect()

    def teardown():
        connection.close()
        engine.dispose()

        db_engine = create_engine(url)
        with db_engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            conn.execute(text(f"DROP DATABASE {test_db_name};"))

    request.addfinalizer(teardown)
    return connection


@pytest.fixture(scope="class", autouse=True)
def setup_db(connection, request: pytest.FixtureRequest) -> None:
    """Setup test database.

    Creates all database tables as declared in SQLAlchemy models,
    then proceeds to drop all the created tables after all tests
    have finished running.
    """

    ORMBase.metadata.create_all(connection.engine)

    def teardown():
        ORMBase.metadata.drop_all(connection.engine)

    request.addfinalizer(teardown)

    return None


@pytest.fixture(autouse=True)
def session(connection, request: pytest.FixtureRequest):
    transaction = connection.begin()
    session = scoped_session(sessionmaker(
        bind=connection, expire_on_commit=False))

    session.begin_nested()

    # Restart savepoint after each commit (do I want this?)
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(db_session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.expire_all()
            session.begin_nested()

    def teardown():
        session.remove()
        if transaction.is_active:
            transaction.rollback()

    request.addfinalizer(teardown)
    return session


@pytest.fixture()
def project(session) -> Project:
    project = Project(
        name='test_project',
        description='test_description',
        starttime=datetime(2024, 1, 1, 0, 0, 0),
        endtime=datetime(2024, 2, 1, 0, 0, 0),
        seismicityobservation_required=EInput.REQUIRED,
        injectionobservation_required=EInput.NOT_ALLOWED,
        injectionplan_required=EInput.NOT_ALLOWED,
        fdsnws_url='https://'
    )

    project = ProjectRepository.create(session, project)

    return project


@pytest.fixture()
def forecastseries(session, project):
    forecastseries = ForecastSeries(
        name='test_forecastseries',
        forecast_starttime=datetime(2021, 1, 2, 0, 0, 0),
        forecast_endtime=datetime(2021, 1, 4, 0, 0, 0),
        observation_starttime=datetime(2021, 1, 1, 0, 0, 0),
        project_oid=project.oid,
        status=EStatus.PENDING,
        forecast_interval=1800,
        bounding_polygon=Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]),
        depth_min=0,
        depth_max=1,
        tags=['tag1', 'tag2']
    )

    forecastseries = ForecastSeriesRepository.create(session, forecastseries)

    return forecastseries


@pytest.fixture()
def forecast(session, forecastseries):
    forecast = Forecast(
        name='test_forecast',
        forecastseries_oid=forecastseries.oid,
        status=EStatus.PENDING,
        starttime=datetime(2021, 1, 2, 0, 30, 0),
        endtime=datetime(2021, 1, 4, 0, 0, 0),
    )

    forecast = ForecastRepository.create(session, forecast)

    return forecast


@pytest.fixture()
def model_config(session):
    model_config = ModelConfig(
        name='test_model',
        description='test_description',
        tags=['tag1', 'tag3'],
        result_type=EResultType.CATALOG,
        enabled=True,
        sfm_module='test_module',
        sfm_function='test_function',
        model_parameters={'setting1': 'value1',
                          'setting2': 'value2'}
    )
    model_config = ModelConfigRepository.create(session, model_config)
    return model_config
