# -*- encoding: utf-8 -*-
"""
History of hydraulic events, i.e changes in flow or pressure

"""

import logging
import traceback

from PyQt4 import QtCore
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship, reconstructor
from ormbase import OrmBase, DeclarativeQObjectMeta

log = logging.getLogger(__name__)


class InjectionHistory(QtCore.QObject, OrmBase):
    """
    Provides a history of hydraulic events and functions to read and write them
    from/to a persistent store. The class uses Qt signals to signal changes.

    """
    __metaclass__ = DeclarativeQObjectMeta

    # region ORM Declarations
    __tablename__ = 'injection_histories'
    id = Column(Integer, primary_key=True)
    # Project relation
    project_id = Column(Integer, ForeignKey('projects.id'))
    project = relationship('Project', back_populates='injection_history')
    # InjectionSample relation
    samples = relationship('InjectionSample',
                           back_populates='injection_history',
                           cascade='all')
    # endregion
    history_changed = QtCore.pyqtSignal()

    @reconstructor
    def init_on_load(self):
        QtCore.QObject.__init__(self)

    def import_events(self, importer):
        """
        Imports hydraulic events from a csv file by using an EventReporter

        The EventReporter must return the following fields (which must thus
        be present in the csv file). All imported events are simply added to
        any existing one. If you want to overwrite existing events, call
        :meth:`clear_events` first.

        - ``flow_dh``: flow down hole [l/min]
        - ``flow_xt``: flow @ x-mas tree (top hole) [l/min]
        - ``pr_dh``: pressure down hole [bar]
        - ``pr_xt``: pressure @ x-mas tree (top hole) [bar]

        :param importer: an EventReporter object
        :type importer: EventImporter

        """
        events = []
        try:
            for date, fields in importer:
                event = InjectionSample(date,
                                        flow_dh=float(
                                            fields.get('flow_dh') or 0),
                                        flow_xt=float(
                                            fields.get('flow_xt') or 0),
                                        pr_dh=float(fields.get('pr_dh') or 0),
                                        pr_xt=float(fields.get('pr_xt') or 0))
                events.append(event)
        except:
            log.error('Failed to import hydraulic events. Make sure '
                      'the .csv file contains top and bottom hole '
                      'flow and pressure fields and that the date '
                      'field has the format dd.mm.yyyyTHH:MM:SS. The '
                      'original error was ' + traceback.format_exc())
        else:
            self.samples.append(events)
            log.info('Imported {} hydraulic events.'.format(
                len(events)))
            self.history_changed.emit()

    def clear_events(self, time_range=None):
        """
        Clear all hydraulic events from the database

        If time_range is given, only the events that fall into the time range

        """
        if time_range:
            to_delete = (s for s in self.samples
                         if time_range[1] >= s.date_time >= time_range[0])
            for s in to_delete:
                self.samples.remove(s)
        else:
            self.samples = []
            log.info('Cleared all hydraulic events.')
        self.history_changed.emit()

    def __getitem__(self, item):
        return self.samples[item] if self.samples else None

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


class InjectionPlan(OrmBase):

    # region ORM Declarations
    __tablename__ = 'injection_plans'
    id = Column(Integer, primary_key=True)
    # InjectionSample relation
    samples = relationship('InjectionSample',
                           back_populates='injection_plan')
    # Scenario relation
    scenarios_id = Column(Integer, ForeignKey('scenarios.id'))
    scenarios = relationship('Scenario', back_populates='injection_plans')
    # endregion


class InjectionSample(OrmBase):
    """
    Represents a hydraulic event (i.e. a flowrate and pressure)

    :ivar datetime.datetime date_time: Date and time when the event occurred
    :ivar float flow_dh: Flow downhole [l/min]
    :ivar float float flow_xt: Flow @ x-mas tree (top hole) [l/min]
    :ivar float pr_dh: pressure downhole [bar]
    :ivar float pr_xt: pressure @ x-mas tree (top hole) [bar]

    """

    # region ORM declarations
    __tablename__ = 'injection_samples'
    id = Column(Integer, primary_key=True)
    date_time = Column(DateTime)
    flow_dh = Column(Float)
    flow_xt = Column(Float)
    pr_dh = Column(Float)
    pr_xt = Column(Float)
    # InjectionHistory relation
    injection_history_id = Column(Integer,
                                  ForeignKey('injection_histories.id'))
    injection_history = relationship('InjectionHistory',
                                     back_populates='samples')
    # InjectionPlan relation
    injection_plan_id = Column(Integer,
                               ForeignKey('injection_plans.id'))
    injection_plan = relationship('InjectionPlan',
                                  back_populates='samples')
    # endregion

    # Data attributes (required for flattening)
    data_attrs = ['date_time', 'flow_dh', 'flow_xt', 'pr_dh', 'pr_xt']

    def copy(self):
        """ Returns a new copy of itself """

        arguments = {}
        for name, column in self.__mapper__.columns.items():
            if not (column.primary_key or column.unique):
                arguments[name] = getattr(self, name)
        copy = self.__class__(self.date_time, self.flow_dh, self.flow_xt,
                              self.pr_dh, self.pr_xt)
        for item in arguments.items():
            setattr(copy, *item)
        return copy

    def __init__(self, date_time, flow_dh, flow_xt, pr_dh, pr_xt):
        """
        The initialisation parameters are the same as the member variables.
        See class description for details.

        """
        self.date_time = date_time
        self.flow_dh = flow_dh
        self.flow_xt = flow_xt
        self.pr_dh = pr_dh
        self.pr_xt = pr_xt

    def __str__(self):
        return "Flow: %.1f @ %s" % (self.flow_dh, self.date_time.ctime())

    def __repr__(self):
        return "<InjectionSample('{}' @ '{}')>"\
            .format(self.flow_dh, self.date_time)

    def __eq__(self, other):
        if isinstance(other, InjectionSample):
            same = (self.date_time == other.date_time and
                    self.flow_dh == other.flow_dh and
                    self.flow_xt == other.flow_xt and
                    self.pr_dh == other.pr_dh and
                    self.pr_xt == other.pr_xt)
            return same
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        else:
            return not result
