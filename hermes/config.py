# Copyright 2019, ETH Zurich - Swiss Seismological Service SED

import collections
import operator
import logging
import yaml
from functools import reduce
"""
RT-RAMSIS settings and defaults.
"""

FDSNWS_NOCONTENT_CODES = (204, 404)


class Settings:
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
