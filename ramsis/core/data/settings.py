# -*- encoding: utf-8 -*-
"""
Settings access and storage

"""

import json
import logging
from datetime import datetime
from sqlalchemy import Column, orm
from sqlalchemy import Integer, String, DateTime
from ormbase import OrmBase

log = logging.getLogger(__name__)


class Settings(OrmBase):
    """
    Collection of settings

    Each Settings object manages a arbitrary number of settings and their
    default values. Internally everything is stored in a nested dict and
    persisted as a json string.

    """

    # region ORM declarations
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    date = Column(DateTime)
    data = Column(String)
    # endregion

    def __init__(self, name):
        self.name = name
        self.date = datetime.now()
        self._dict = {}

    @orm.reconstructor
    def init_on_load(self):
        self._dict = json.loads(self.data) if self.data else {}

    def add(self, name, value=None, title=None, default=None):
        """
        Add a new setting

        :param name: name to retrieve the setting later
        :param value: value, if None the default will be returned on access
        :param title: display title, if None name will be used
        :param default: default value

        """
        s = {'title': title or name, 'default': default}
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

    def title(self, name):
        """ Return the display title for a setting """
        s = self._dict[name]
        return s['title']

    def commit(self):
        """
        Commit the settings

        This just updates the internal json string and the date if we keep
        a history of this Settings object. You still need to commit the object
        to the database afterwards.

        """
        self.date = datetime.now()
        self.data = json.dumps(self._dict)
