# -*- encoding: utf-8 -*-
"""
Settings access and storage

These classes represent project related settings, i.e. settings
that will be stored in the project database.

"""

import json
import logging
from datetime import datetime
from PyQt4 import QtCore
from sqlalchemy import Column, orm
from sqlalchemy import Integer, String, DateTime
from ormbase import OrmBase, DeclarativeQObjectMeta

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


class Settings(QtCore.QObject, OrmBase):
    """
    Collection of settings

    Each Settings object manages a arbitrary number of settings and their
    default values. Internally everything is stored in a nested dict and
    persisted as a json string. This makes it easy to add new and remove
    obsolete settings.

    """
    __metaclass__ = DeclarativeQObjectMeta

    # region ORM declarations
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    date = Column(DateTime)
    data = Column(String)
    __mapper_args__ = {'polymorphic_on': name}
    # endregion

    settings_changed = QtCore.pyqtSignal(object)

    def __init__(self):
        super(Settings, self).__init__()
        self.date = datetime.now()
        self._dict = {}

    @orm.reconstructor
    def init_on_load(self):
        QtCore.QObject.__init__(self)
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

        This updates the internal json string and the date property if we keep
        a history of this Settings object. You still need to commit the object
        to the database afterwards.
        Emits the settings_changed signal

        """
        self.date = datetime.now()
        self.data = json.dumps(self._dict, indent=4, default=datetime_encoder)
        self.settings_changed.emit(self)


class ProjectSettings(Settings):

    __mapper_args__ = {'polymorphic_identity': 'project'}

    default_settings = {
        'fdsnws_enable': False,
        'fdsnws_url': None,
        'fdsnws_interval': 5.0,  # minutes
        'hydws_enable': False,
        'hydws_url': None,
        'hydws_interval': 5.0,  # minutes
        'rate_interval': 1.0,  # minutes
        'auto_schedule_enable': True,
        'forecast_interval': 6.0,  # hours
        'forecast_length': 6.0,  # hours
        'forecast_start': datetime(1970, 1, 1, 0, 0, 0),
        'seismic_rate_interval': 1.0,  # minutes
        'forecast_models': {
            'rj': {
                'enabled': True,
                'url': 'http://localhost:5000/run',
                'title': 'Reasenberg-Jones',
                'parameters': {'a': -1.6, 'b': 1.58, 'p': 1.2, 'c': 0.05}
            },
            'etas': {
                'enabled': True,
                'url': 'http://localhost:5001/run',
                'title': 'ETAS',
                'parameters': {'alpha': 0.8, 'k': 8.66, 'p': 1.2, 'c': 0.01,
                               'mu': 12.7, 'cf': 1.98}
            },
            'shapiro': {
                'enabled': False,
                'url': 'http://localhost:5002/run',
                'title': 'Shapiro (spatial)',
                'parameters': None
            },
        },
        'write_fc_results_to_disk': False,
    }

    def __init__(self):
        super(ProjectSettings, self).__init__()

        for key, default_value in self.default_settings.items():
            self.add(key, default=default_value)
        self.commit()
