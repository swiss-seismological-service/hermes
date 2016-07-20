# -*- encoding: utf-8 -*-
"""
History of hydraulic events, i.e changes in flow or pressure

"""

import logging
import traceback

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ormbase import OrmBase, DeclarativeQObjectMeta
from core.data.eventhistory import EventHistory


class InjectionHistory(EventHistory, OrmBase):
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

    def __init__(self, store):
        EventHistory.__init__(self, store, InjectionSample)
        self._logger = logging.getLogger(__name__)

    def import_events(self, importer, timerange=None):
        """
        Imports seismic events from a csv file by using an EventReporter

        The EventReporter must return the following fields (which must thus
        be present in the csv file)

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
            self._logger.error('Failed to import hydraulic events. Make sure '
                               'the .csv file contains top and bottom hole '
                               'flow and pressure fields and that the date '
                               'field has the format dd.mm.yyyyTHH:MM:SS. The '
                               'original error was ' +
                               traceback.format_exc())
        else:
            predicate = None
            if timerange:
                predicate = (self.entity.date_time >= timerange[0],
                             self.entity.date_time <= timerange[1])
            self.store.purge_entity(self.entity, predicate)
            self.store.add(events)
            self._logger.info('Imported {} hydraulic events.'.format(
                len(events)))
            self.reload_from_store()
            self._emit_change_signal({})


class InjectionPlan(OrmBase):

    # region ORM Declarations
    __tablename__ = 'injection_plans'
    id = Column(Integer, primary_key=True)
    # ForecastInput relation
    forecast_input_id = Column(Integer, ForeignKey('forecast_inputs.id'))
    forecast_input = relationship('ForecastInput',
                                  back_populates='injection_plan',
                                  uselist=False)
    # InjectionSample relation
    samples = relationship('InjectionSample',
                           back_populates='injection_plan')
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
    __tablename__ = 'hydraulicevents'
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
