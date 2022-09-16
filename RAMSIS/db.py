import os
from os.path import abspath, dirname
from os import getenv
import collections
import operator
import logging
import yaml
from functools import reduce
from dotenv import dotenv_values

from RAMSIS.core.store import Store


class AppSettings:
    """
    Global application settings.

    To access settings through this class.

    """

    def __init__(self, settings_file=None):
        """
        Load either the default settings or, if a file name is
        provided, specific settings from that file.

        """
        self._settings_file = settings_file
        self._logger = logging.getLogger(__name__)
        if settings_file is None:
            settings_file = 'settings.yml'

        self._logger.info('Loading settings from ' + settings_file)
        with open(settings_file, 'r') as f:
            self.settings = yaml.full_load(f.read())

    def all(self):
        """ Return all settings as a flat dict: {'section/key': value} """
        def flatten(d, parent_key='', sep='/'):
            items = []
            for k, v in d.items():
                new_key = parent_key + sep + k if parent_key else k
                if isinstance(v, collections.MutableMapping):
                    items.extend(flatten(v, new_key, sep=sep).items())
                else:
                    items.append((new_key, v))
            return dict(items)

        return flatten(self.settings)

    def __getitem__(self, key):
        return reduce(operator.getitem, key.split('/'), self.settings)

    def __setitem__(self, key, value):
        keys = key.split('/')
        if len(keys) > 1:
            leaf_node = reduce(operator.getitem, keys[:-1], self.settings)
        else:
            leaf_node = self.settings
        leaf_node[keys[-1]] = value


# Load application settings
dir_path = dirname(abspath(__file__))
root_dir = dirname(dir_path)
settings_file = os.path.join(dir_path, '..', 'config',
                             'ramsis_config_public.yml')
if os.path.islink(settings_file):
    settings_file = os.readlink(settings_file)
app_settings = AppSettings(settings_file)

testing_mode = bool(getenv("RAMSIS_TESTING_MODE", False)) is True
print("testing mode: ", testing_mode, getenv("RAMSIS_TESTING_MODE"))
env_file = ".env.test" if testing_mode else ".env"
env_file_path = os.path.join(root_dir, env_file)
env = dotenv_values(env_file_path)


db_url = f'postgresql://{env["POSTGRES_USER"]}:{env["POSTGRES_PASSWORD"]}' \
         f'@{env["POSTGRES_SERVER"]}:{env["POSTGRES_PORT"]}/' \
         f'{env["POSTGRES_DB"]}'

store = Store(db_url)
