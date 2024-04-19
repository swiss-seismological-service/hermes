import os
from os.path import abspath, dirname
from os import getenv
from dotenv import dotenv_values
import logging
import ramsis.datamodel
from ramsis.datamodel.base import ORMBase
import pkgutil
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
import contextlib
import sys

from RAMSIS.config import Settings


logger = logging.getLogger(__name__)


def connect_to_db(connection_string: str):
    engine = create_engine(connection_string)
    session = Session(engine)
    return session


@contextlib.contextmanager
def session_handler(connection_string):
    session = connect_to_db(connection_string)
    yield session
    session.rollback()
    session.close()


def init_db(connection_string: str) -> bool:
    """
    Initializes the db

    Creates the table defined in the ORM meta data.

    :returns: True if successful
    :rtype: bool
    """
    # We need to make sure all datamodel modules are imported at least once
    # for the ORMBase meta data to be complete; ensure that ORMBase has all the
    # metadata
    pkg = ramsis.datamodel
    modules = pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__ + '.')
    modules = [m for m in modules if 'tests' not in m[1]]
    for finder, module_name, _ in modules:
        if module_name not in sys.modules:
            finder.find_module(module_name).load_module(module_name)
    engine = create_engine(connection_string)
    try:
        ORMBase.metadata.create_all(engine, checkfirst=True)
    except SQLAlchemyError as e:
        logger.error(f'Error while initializing DB: {e}')
        return False
    return True


# Load application settings
dir_path = dirname(abspath(__file__))
root_dir = dirname(dir_path)
settings_file = os.path.join(dir_path, '..', 'config',
                             'ramsis_config_public.yml')
if os.path.islink(settings_file):
    settings_file = os.readlink(settings_file)
app_settings = Settings(settings_file)

testing_mode = bool(getenv("RAMSIS_TESTING_MODE", False)) is True
testing_mode = os.getenv("RAMSIS_TESTING_MODE", 'False').lower() in \
    ('true', '1', 't')
project = app_settings['project']
print("testing mode: ", testing_mode)
env_file = ".env.test" if testing_mode else ".env"
env_file_path = os.path.join(root_dir, env_file)
env = dotenv_values(env_file_path)


db_url = f'postgresql://{env["POSTGRES_USER"]}:{env["POSTGRES_PASSWORD"]}' \
         f'@{env["POSTGRES_SERVER"]}:{env["POSTGRES_PORT"]}/' \
         f'{env["POSTGRES_DB"]}'
