import pytest
from os import environ
import psycopg2

testing_environment_variable = "RAMSIS_TESTING_MODE"

# in db.py the db credentials will come from the env.test file instead of .env
TEMP_ENV_VARS = {testing_environment_variable: 'true'}


def pytest_addoption(parser):
    parser.addoption("--use-data-ws", default=False,
                     dest='use_data_ws', action='store_true')
    parser.addoption("--use-model-ws", default=False,
                     dest='use_model_ws', action='store_true')


@pytest.fixture
def use_model_ws(pytestconfig):
    return pytestconfig.getoption("use_model_ws")


@pytest.fixture
def use_data_ws(pytestconfig):
    return pytestconfig.getoption("use_data_ws")


@pytest.fixture(scope='session')
def env():
    old_environ = dict(environ)
    environ.update(TEMP_ENV_VARS)
    from RAMSIS.db import env as environment
    yield environment
    environ.clear()
    environ.update(old_environ)


@pytest.fixture(scope='function')
def session():
    from RAMSIS.db import connect_to_db, db_url
    session = connect_to_db(db_url)
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope='function')
def connection(env):
    connection = psycopg2.connect(
        port=env["POSTGRES_PORT"], user=env["DEFAULT_USER"],
        host=env["POSTGRES_SERVER"], password=env["DEFAULT_PASSWORD"],
        dbname=env["DEFAULT_DB"])
    connection.autocommit = True
    yield connection
    connection.close()


@pytest.fixture(scope="function", autouse=True)
def setup_database(connection, env):
    try:
        user = env["POSTGRES_USER"]
        password = env["POSTGRES_PASSWORD"]
        dbname = env["POSTGRES_DB"]
    except KeyError as err:
        print(f"Key does not exist env: {env}, err: {err}")
        raise
    cursor = connection.cursor()
    cursor.execute(
        "select pg_terminate_backend(pg_stat_activity.pid)"
        " from pg_stat_activity where pg_stat_activity.datname="
        f"'{dbname}' AND pid <> pg_backend_pid()")
    cursor.execute(f"DROP DATABASE IF EXISTS {dbname}")
    cursor.execute(f"DROP USER IF EXISTS {user}")
    cursor.execute(f"CREATE USER {user} with password "
                   f"'{password}' SUPERUSER")
    cursor.execute(f"CREATE DATABASE {dbname} with owner "
                   f"{user}")
    cursor.close()
    # Register workpool here?

    yield
    cursor = connection.cursor()
    cursor.execute(
        "select pg_terminate_backend(pg_stat_activity.pid)"
        " from pg_stat_activity where pg_stat_activity.datname="
        f"'{dbname}' AND pid <> pg_backend_pid()")
    cursor.close()
    # # Activate following section if there are leftover running connections
    # # after tests have completed. Causes warning to be issues.
    # conn = psycopg2.connect(
    #     port=env["POSTGRES_PORT"], user=env["DEFAULT_USER"],
    #     host=env["POSTGRES_SERVER"], password=env["DEFAULT_PASSWORD"],
    #     dbname=env["DEFAULT_DB"])
    # conn.autocommit = True
    # cursor = conn.cursor()
    # cursor.execute(
    #     "select pg_terminate_backend(pg_stat_activity.pid)"
    #     " from pg_stat_activity where pg_stat_activity.datname="
    #     f"'{postgres_db}' AND pid <> pg_backend_pid()")
    # cursor.close()
    # conn.close()
    # print("after after setup yield")
    # sleep(10)
