# -*- encoding: utf-8 -*-
"""
History of seismic events

"""

import logging
import traceback

from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ormbase import OrmBase

from core.data.eventhistory import EventHistory
from core.data.seismicevent import SeismicEvent
from core.data.geometry import Point


class SeismicCatalog(EventHistory, OrmBase):
    """
    Provides a history of seismic events and functions to read and write them
    from/to a persistent store. The class uses Qt signals to signal changes.

    """

    # region ORM Declarations
    __tablename__ = 'seismic_catalogs'
    id = Column(Integer, primary_key=True)
    # Project relation
    project_id = Column(Integer, ForeignKey('projects.id'))
    project = relationship('Project', back_populates='seismic_catalog')
    # SeismicEvent relation (we own them)
    seismic_events = relationship('SeismicEvent',
                                  back_populates='seismic_catalog',
                                  cascade='all, delete-orphan')
    # endregion

    def __init__(self, store):
        EventHistory.__init__(self, store, SeismicEvent)
        self._logger = logging.getLogger(__name__)

    def import_events(self, importer, timerange=None):
        """
        Imports seismic events from a csv file by using an EventImporter

        The EventImporter must return the following fields (which must thus
        be present in the csv file)

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
            self._logger.error('Failed to import seismic events. Make sure '
                               'the .csv file contains x, y, depth, and mag '
                               'fields and that the date field has the format '
                               'dd.mm.yyyyTHH:MM:SS. The original error was ' +
                               traceback.format_exc())
        else:
            predicate = None
            if timerange:
                predicate = (self.entity.date_time >= timerange[0],
                             self.entity.date_time <= timerange[1])
            self.store.purge_entity(self.entity, predicate)
            self.store.add(events)
            self._logger.info('Imported {} seismic events.'.format(
                len(events)))
            self.reload_from_store()
            self._emit_change_signal({})

    def events_before(self, end_date, mc=0):
        """ Returns all events >mc before and including *end_date* """
        return [e for e in self._events
                if e.date_time < end_date and e.magnitude > mc]


class SnapshotCatalog(EventHistory, OrmBase):
    """
    A snapshot of a seismic catalog.

    The snapshot catalog consists of snapshots of events. Each snapshot has the
    preferred origin and magnitude at the time the snapshot was taken.

    """

    # region ORM Declarations
    __tablename__ = 'snapshot_catalogs'
    id = Column(Integer, primary_key=True)
    snapshot_time = Column(DateTime)
    # Snapshots relation
    snapshots = relationship('EventSnapshot',
                             back_populates='snapshot_catalog',
                             cascade='all, delete-orphan')
    # ForecastInput relation
    forecast_input = relationship('ForecastInput', uselist=False,
                                  back_populates='input_catalog')
    # SkillTest relation
    skill_test = relationship('SkillTest', uselist=False,
                              back_populates='reference_catalog')
    # endregion



class EventSnapshot(OrmBase):

    # region ORM Declarations
    __tablename__ = 'event_snapshots'
    id = Column(Integer, primary_key=True)
    # SnapshotCatalog relation
    snapshot_catalog_id = Column(Integer, ForeignKey('snapshot_catalog.id'))
    snapshot_catalog = relationship('SnapshotCatalog',
                                    back_populates='snapshots')
    # SeismicEvent relation
    seismic_event_id = Column(Integer, ForeignKey('seismic_event.id'))
    seismic_event = relationship('SeismicEvent', back_populates='snapshots')
    # Pseudo relations to preferred origin/magnitude at time of snapshot
    preferred_origin_id = Column(Integer, ForeignKey('origins.id'))
    origin = relationship('Origin', uselist=False)
    preferred_magnitude_id = Column(Integer, ForeignKey('magnitudes.id'))
    magnitude = relationship('Magnitude', uselist=False)
    # endregion

class SeismicEvent(OrmBase):
    """Represents a seismic event

    :ivar date_time: Date and time when the event occurred
    :type date_time: datetime
    :ivar magnitude: Event magnitude
    :type magnitude: float
    :ivar x: Event x coordinate
    :type x: float
    :ivar y: Event y coordinate [m]
    :type y: float
    :ivar z: Event depth [m] (0 at surface, positive downwards)
    :type z: float

    :param datetime.datetime date_time: Date and time of the event
    :param float magnitude: Event magnitude
    :param Point location: Event coordinates

    """

    # region ORM declarations
    __tablename__ = 'seismic_events'
    id = Column(Integer, primary_key=True)
    public_id = Column(String)
    # SeismicCatalog relation
    seismic_catalog_id = Column(Integer, ForeignKey('seismic_catalogs.id'))
    seismic_catalog = relationship('SeismicCatalog',
                                   back_populates='seismic_events')
    # EventSnapshot relation
    snapshots = relationship('EventSnapshot',
                             back_populates='seismic_event',
                             cascade='all, delete-orphan')
    # Magnitude relation
    magnitudes = relationship('Magnitude',
                              back_populates='seismic_event',
                              cascade='all, delete-orphan')
    preferred_magnitude_id = Column(Integer, ForeignKey('magnitudes.id'))
    magnitude = relationship('Magnitude', uselist=False,
                             foreign_keys=[preferred_magnitude_id])
    # Origin relation
    origins = relationship('Origin',
                           back_populates='seismic_event',
                           cascade='all, delete-orphan')
    preferred_origin_id = Column(Integer, ForeignKey('origins.id'))
    origin = relationship('Origin', uselist=False,
                          foreign_keys=[preferred_origin_id])
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

    def __init__(self, date_time, magnitude, location):
        self.origin = Origin(date_time, location)
        self.magnitude = Magnitude(magnitude)

    def __str__(self):
        return "M%.1f @ %s" % (self.magnitude.magnitude,
                               self.origin.date_time.ctime())

    def __repr__(self):
        return "<SeismicEvent('%s' @ '%s')>" % (self.magnitude.magnitude,
                                                self.origin.date_time)

    def __eq__(self, other):
        if isinstance(other, SeismicEvent):
            return (self.origin == other.origin and
                    self.magnitude == other.magnitude)
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        else:
            return not result

class Origin(OrmBase):

    # region ORM Declarations
    __tablename__ = 'origins'
    id = Column(Integer, primary_key=True)
    public_id = Column(String)
    seismic_event_id = Column(Integer, ForeignKey('seismic_events.id'))
    seismic_event = relationship('SeismicEvent', back_populates='origins',
                                 foreign_keys=seismic_event_id)
    date_time = Column(DateTime)
    lat = Column(Float)
    lon = Column(Float)
    depth = Column(Float)
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)

    # endregion

    def __init__(self, date_time, location):
        self.date_time = date_time
        self.x = location.x
        self.y = location.y
        self.z = location.z

    def __eq__(self, other):
        if isinstance(other, Origin):
            return (self.x == other.x and
                    self.y == other.y and
                    self.z == other.z)
        return NotImplemented

class Magnitude(OrmBase):

    # region ORM Declarations
    __tablename__ = 'magnitudes'
    id = Column(Integer, primary_key=True)
    public_id = Column(String)
    seismic_event_id = Column(Integer, ForeignKey('seismic_events.id'))
    seismic_event = relationship('SeismicEvent',
                                 back_populates='magnitudes',
                                 foreign_keys=seismic_event_id)
    magnitude = Column(Float)

    # endregion

    def __init__(self, magnitude):
        self.magnitude = magnitude

    def __eq__(self, other):
        if isinstance(other, Magnitude):
            return self.magnitude == other.magnitude
        return NotImplemented
