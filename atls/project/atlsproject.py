# -*- encoding: utf-8 -*-
"""
Provides a class to manage Atls project data

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import project
from PyQt4 import QtCore
from datetime import datetime
from seismiceventhistory import SeismicEventHistory
from hydrauliceventhistory import HydraulicEventHistory
from domainmodel.injectionwell import InjectionWell
from eqstats import SeismicRateHistory


class AtlsProject(project.Project):
    """
    Manages persistent and non-persistent atls project data such as the seismic
    and hydraulic history, and project state information.

    .. pyqt4:signal:project_time_changed: emitted when the project time changes

    :ivar seismic_history: The seismic history of the project
    :ivar hydraulic_history: The hydraulic history of the project
    :ivar path: Path of the project file (non persistent)
    :ivar project_time: Current project time (non persistent)

    """

    # Signals
    project_time_changed = QtCore.pyqtSignal(datetime)

    def __init__(self, store):
        """ Create a project based on the data that is contained in *store* """
        super(AtlsProject, self).__init__(store)
        self.seismic_history = SeismicEventHistory(self._store)
        self.seismic_history.reload_from_store()
        self.hydraulic_history = HydraulicEventHistory(self._store)
        self.hydraulic_history.reload_from_store()
        self.rate_history = SeismicRateHistory()

        # FIXME: hardcoded for testing purposes
        # These are the basel well coordinates (CH-1903: 270645.0 / 611631.0)
        self.injection_well = InjectionWell(4740.3, 47.5864, 7.5932)

        # Set the project time to the time of the first event
        event = self.earliest_event()
        self._project_time = event.date_time if event else None

    @property
    def project_time(self):
        return self._project_time

    # Event information

    def event_time_range(self):
        """
        Returns the time range of all events in the project as a (start_time,
        end_time) tuple.

        """
        earliest = self.earliest_event()
        latest = self.latest_event()
        return earliest.date_time, latest.date_time

    def earliest_event(self):
        """
        Returns the earliest event in the project, either seismic or hydraulic.

        """
        es = self.seismic_history[0]
        eh = self.hydraulic_history[0]
        if es is None and eh is None:
            return None
        elif es is None:
            return eh
        elif eh is None:
            return es
        else:
            return eh if eh.date_time < es.date_time else es

    def latest_event(self):
        """
        Returns the latest event in the project, either seismic or hydraulic.

        """
        es = self.seismic_history[-1]
        eh = self.hydraulic_history[-1]
        if es is None and eh is None:
            return None
        elif es is None:
            return eh
        elif eh is None:
            return es
        else:
            return eh if eh.date_time > es.date_time else es

    # Project time

    def update_project_time(self, t):
        self._project_time = t
        self.project_time_changed.emit(t)
