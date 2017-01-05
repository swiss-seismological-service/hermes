# -*- encoding: utf-8 -*-
"""
History of seismic events

"""

import logging
import traceback

from PyQt4 import QtCore
from sqlalchemy import Column, Table
from sqlalchemy import Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ormbase import OrmBase, DeclarativeQObjectMeta

from core.data.geometry import Point

_catalogs_events_table = Table('catalogs_events', OrmBase.metadata,
                               Column('seismic_catalogs_id', Integer,
                                      ForeignKey('seismic_catalogs.id')),
                               Column('seismic_events_id', Integer,
                                      ForeignKey('seismic_events.id')))

log = logging.getLogger(__name__)


class SeismicCatalog(QtCore.QObject, OrmBase):
    """
    Provides a history of seismic events and functions to read and write them
    from/to a persistent store. The class uses Qt signals to signal changes.

    """
    __metaclass__ = DeclarativeQObjectMeta

    # region ORM Declarations
    __tablename__ = 'seismic_catalogs'
    id = Column(Integer, primary_key=True)
    catalog_date = Column(DateTime)
    # SeismicEvent relation (we own them)
    seismic_events = relationship('SeismicEvent',
                                  order_by='SeismicEvent.date_time',
                                  secondary=_catalogs_events_table,
                                  back_populates='seismic_catalog')
    # Parents
    # ...Project relation
    project_id = Column(Integer, ForeignKey('projects.id'))
    project = relationship('Project', back_populates='seismic_catalog')
    # ...ForecastInput relation
    forecast_input_id = Column(Integer, ForeignKey('forecast_inputs.id'))
    forecast_input = relationship('ForecastInput',
                                  back_populates='input_catalog')
    # ...SkillTest relation
    skill_test_id = Column(Integer, ForeignKey('skill_tests.id'))
    skill_test = relationship('SkillTest',
                              back_populates='reference_catalog')
    # endregion
    catalog_changed = QtCore.pyqtSignal()

    def import_events(self, importer):
        """
        Imports seismic events from a csv file by using an EventImporter

        The EventImporter must return the following fields (which must thus
        be present in the csv file). All imported events are simply added to
        any existing one. If you want to overwrite existing events, call
        :meth:`clear_events` first.

        x: x coordinate [m]
        y: y coordinate [m]
        depth: depth [m], positive downwards
        mag: magnitude

        :param importer: an EventImporter object
        :type importer: EventImporter

        """
        events = []
        try:
            for date, fields in importer:
                location = Point(float(fields['x']),
                                 float(fields['y']),
                                 float(fields['depth']))
                event = SeismicEvent(date, float(fields['mag']), location)
                events.append(event)
        except:
            log.error('Failed to import seismic events. Make sure '
                      'the .csv file contains x, y, depth, and mag '
                      'fields and that the date field has the format '
                      'dd.mm.yyyyTHH:MM:SS. The original error was ' +
                      traceback.format_exc())
        else:
            self.seismic_events.append(events)
            log.info('Imported {} seismic events.'.format(len(events)))
            self.catalog_changed.emit()

    def events_before(self, end_date, mc=0):
        """ Returns all events >mc before and including *end_date* """
        return [e for e in self._events
                if e.date_time < end_date and e.magnitude > mc]

    def clear_events(self, time_range=None):
        """
        Clear all seismic events from the database

        If time_range is given, only the events that fall into the time range

        """
        if time_range:
            to_delete = (s for s in self.seismic_events
                         if time_range[1] >= s.date_time >= time_range[0])
            for s in to_delete:
                self.seismic_events.remove(s)
        else:
            self.seismic_events = []
            log.info('Cleared all hydraulic events.')
        self.catalog_changed.emit()

    def __len__(self):
        return len(self.seismic_events)

    def __getitem__(self, item):
        return self.seismic_events[item] if self.seismic_events else None

    def copy(self):
        """ Returns a new copy of itself """

        arguments = {}
        for name, column in self.__mapper__.columns.items():
            if not (column.primary_key or column.unique):
                arguments[name] = getattr(self, name)
        copy = self.__class__()
        for item in arguments.items():
            setattr(copy, *item)
        return copy


class SeismicEvent(OrmBase):
    """
    Represents a seismic event

    A seismic event consists of at least one magnitude and one origin. Multiple
    magnitudes and origins can be present for a single event. In that case, the
    members *magnitude* and *origin* will point to the preferred magnitude and
    origin respectively.

    """

    # region ORM declarations
    __tablename__ = 'seismic_events'
    id = Column(Integer, primary_key=True)
    # Identifiers
    public_id = Column(String)
    public_origin_id = Column(String)
    public_magnitude_id = Column(String)
    # Origin
    date_time = Column(DateTime)
    lat = Column(Float)
    lon = Column(Float)
    depth = Column(Float)
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)
    # Magnitude
    magnitude = Column(Float)
    # SeismicCatalog relation
    seismic_catalog = relationship('SeismicCatalog',
                                   secondary=_catalogs_events_table,
                                   back_populates='seismic_events')
    # endregion

    # Data attributes (required for flattening)
    data_attrs = ['magnitude', 'date_time', 'x', 'y', 'z']

    def in_region(self, region):
        """
        Tests if the event is located inside **region**

        :param Cube region: Region to test (cube)
        :return: True if the event is inside the region, false otherwise

        """
        return Point(self.x, self.y, self.z).in_cube(region)

    def copy(self):
        """ Returns a new copy of itself """

        arguments = {}
        for name, column in self.__mapper__.columns.items():
            if not (column.primary_key or column.unique):
                arguments[name] = getattr(self, name)
        copy = self.__class__(self.date_time, self.magnitude,
                              Point(self.x, self.y, self.z))
        for item in arguments.items():
            setattr(copy, *item)
        return copy

    def __init__(self, date_time, magnitude, location):
        self.date_time = date_time
        self.magnitude = magnitude
        self.x = location.x
        self.y = location.y
        self.z = location.z

    def __str__(self):
        return "M%.1f @ %s" % (self.magnitude, self.date_time.ctime())

    def __repr__(self):
        return "<SeismicEvent('%s' @ '%s')>" % (self.magnitude, self.date_time)

    def __eq__(self, other):
        if isinstance(other, SeismicEvent):
            if self.public_id and other.public_id:
                return self.public_id == other.public_id
            else:
                return all(getattr(self, a) == getattr(other, a)
                           for a in self.data_attrs)
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        else:
            return not result
