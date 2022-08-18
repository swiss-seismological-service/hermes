import pytest
from os import environ
import psycopg2

testing_environment_variable = "RAMSIS_TESTING_MODE"

# in db.py the db credentials will come from the env.test file instead of .env
TEMP_ENV_VARS = {testing_environment_variable: 'true'}


@pytest.fixture(scope="session", autouse=True)
def tests_setup_and_teardown():
    print("tests setup")
    # Will be executed before the first test
    old_environ = dict(environ)
    environ.update(TEMP_ENV_VARS)

    from RAMSIS.db import env  # Postgres credentials now found in environment
    port = env["POSTGRES_PORT"]
    host = env["POSTGRES_SERVER"]
    user = env["POSTGRES_USER"]
    password = env["POSTGRES_PASSWORD"]
    dbname = env["POSTGRES_DB"]
    default_user = env["DEFAULT_USER"]
    default_password = env["DEFAULT_PASSWORD"]
    default_dbname = env["DEFAULT_DB"]

    conn0 = psycopg2.connect(
        port=port, user=default_user,
        host=host, password=default_password,
        dbname=default_dbname)
    conn0.autocommit = True
    cursor0 = conn0.cursor()
    cursor0.execute(f"DROP DATABASE IF EXISTS {dbname}")
    cursor0.execute(f"DROP USER IF EXISTS {user}")
    cursor0.execute(f"CREATE USER {user} with password "
                    f"'{password}' SUPERUSER")
    cursor0.execute(f"CREATE DATABASE {dbname} with owner "
                    f"{user}")
    cursor0.execute(
        "select pg_terminate_backend(pg_stat_activity.pid)"
        " from pg_stat_activity where pg_stat_activity.datname="
        f"'{dbname}' AND pid <> pg_backend_pid()")
    cursor0.close()
    conn0.close()

    yield
    # Activate following section if there are leftover running connections
    # after tests have completed. Causes warning to be issues.
    # conn = psycopg2.connect(
    #     port=port, user=default_user,
    #     host=host, password=default_password,
    #     dbname=default_dbname)
    # conn.autocommit = True
    # cursor = conn.cursor()
    # cursor.execute(
    #     "select pg_terminate_backend(pg_stat_activity.pid)"
    #     " from pg_stat_activity where pg_stat_activity.datname="
    #     f"'{dbname}' AND pid <> pg_backend_pid()")
    # cursor.close()
    # conn.close()

    # Will be executed after the last test
    # old environment will be resumed.
    environ.clear()
    environ.update(old_environ)
