from datetime import datetime

import pytest
from hermes.datamodel import ORMBase
from sqlalchemy import Connection, event, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import scoped_session, sessionmaker

from config import get_settings
from hermes.repositories.db import create_engine, create_extensions
from hermes.repositories.forecastseries import ForecastSeriesRepository
from hermes.repositories.project import ProjectRepository
from hermes.schemas.base import EStatus
from hermes.schemas.forecastseries import ForecastSeries
from hermes.schemas.project import Project

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


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session", autouse=True)
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
def project(session):
    project = Project(name='test_project', starttime=datetime(2021, 1, 1))
    project = ProjectRepository.create(session, project)

    return project


@pytest.fixture()
def forecastseries(session, project):
    forecastseries = ForecastSeries(
        name='test_forecastseries',
        forecast_starttime=datetime(2021, 1, 1),
        project_oid=project.oid,
        status=EStatus.PENDING)

    forecastseries = ForecastSeriesRepository.create(session, forecastseries)

    return forecastseries
