# -*- encoding: utf-8 -*-
"""
Settings access and storage

These classes represent project related settings, i.e. settings
that will be stored in the project database.

"""

import json
import logging
from datetime import datetime
from sqlalchemy import Column, orm
from sqlalchemy import Integer, String, DateTime
from ormbase import OrmBase

log = logging.getLogger(__name__)

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def datetime_encoder(x):
    if isinstance(x, datetime):
        return x.strftime(DATE_FORMAT)
    raise TypeError('Don''t know how to encode {}'.format(x))


def datetime_decoder(dct):
    for k, v in dct.items():
        if isinstance(v, basestring):
            try:
                dct[k] = datetime.strptime(v, DATE_FORMAT)
            except ValueError:
                pass
    return dct


class Settings(OrmBase):
    """
    Collection of settings

    Each Settings object manages a arbitrary number of settings and their
    default values. Internally everything is stored in a nested dict and
    persisted as a json string. This makes it easy to add new and remove
    obsolete settings.

    """

    # region ORM declarations
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    date = Column(DateTime)
    data = Column(String)
    __mapper_args__ = {'polymorphic_on': name}
    # endregion

    def __init__(self):
        self.date = datetime.now()
        self._dict = {}

    @orm.reconstructor
    def init_on_load(self):
        self._dict = json.loads(self.data, object_hook=datetime_decoder) \
            if self.data else {}

    def add(self, name, value=None, default=None):
        """
        Add a new setting

        :param name: name to retrieve the setting later
        :param value: value, if None the default will be returned on access
        :param default: default value

        """
        s = {'default': default}
        if value:
            s['value'] = value
        self._dict[name] = s

    def __contains__(self, name):
        """ Check if setting is present """
        return name in self._dict

    def __getitem__(self, name):
        """ Return the value for a setting """
        s = self._dict[name]
        if 'value' in s:
            return s['value']
        else:
            return s['default']

    def __setitem__(self, key, value):
        self._dict[key]['value'] = value

    def keys(self):
        """ Return all keys """
        return self._dict.keys()

    def commit(self):
        """
        Commit the settings

        This just updates the internal json string and the date if we keep
        a history of this Settings object. You still need to commit the object
        to the database afterwards.

        """
        self.date = datetime.now()
        self.data = json.dumps(self._dict, indent=4, default=datetime_encoder)


class ProjectSettings(Settings):

    __mapper_args__ = {'polymorphic_identity': 'project'}

    default_settings = {
        'fdsnws_enable': False,
        'fdsnws_url': None,
        'hydws_enable': False,
        'hydws_url': None,
        'auto_schedule_enable': True,
        'forecast_interval': 6.0,
        'forecast_length': 6.0,
        'forecast_start': datetime(1970, 1, 1, 0, 0, 0),
        'seismic_rate_interval': 1.0,
        'active_models': ['all'],
        'write_fc_results_to_disk': False,
    }

    def __init__(self):
        super(ProjectSettings, self).__init__()

        for key, default_value in self.default_settings.items():
            self.add(key, default=default_value)
        self.commit()
