
from os import getenv
from os import environ
import psycopg2

testing_environment_variable = "RAMSIS_TESTING_MODE"

# in db.py the db credentials will come from the env.test file instead of .env
TEMP_ENV_VARS = {testing_environment_variable: 'true'}

def main():
    old_environ = dict(environ)
    environ.update(TEMP_ENV_VARS)
    from RAMSIS.db import env, env_file_path, testing_mode

    connection = psycopg2.connect(
        port=env["POSTGRES_PORT"], user=env["DEFAULT_USER"],
        host=env["POSTGRES_SERVER"], password=env["DEFAULT_PASSWORD"],
        dbname=env["DEFAULT_DB"])
    connection.autocommit = True

    from RAMSIS.db import connect_to_db, db_url
    session = connect_to_db(db_url)

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

    cursor = connection.cursor()
    cursor.execute(
        "select pg_terminate_backend(pg_stat_activity.pid)"
        " from pg_stat_activity where pg_stat_activity.datname="
        f"'{dbname}' AND pid <> pg_backend_pid()")
    cursor.close()
    connection.close()
    session.rollback()
    session.close()
    environ.clear()
    environ.update(old_environ)

if __name__ == "__main__":
    main()
