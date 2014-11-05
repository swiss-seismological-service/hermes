# -*- encoding: utf-8 -*-
"""
ATLS Core Application.

Top level object for the core Atls application. Core meaning it is not
aware of any gui components (or other user control facilities). The user
control facilities should be hooked up in the Atls class instead.

"""

import logging
from datetime import timedelta, datetime

from PyQt4 import QtCore

from project.store import Store
from project.atlsproject import AtlsProject
from domainmodel.datamodel import DataModel
from simulator import Simulator
from engine import Engine

import os
#from tools import Profiler


class AtlsCore(QtCore.QObject):
    """
    Top level class for ATLS i.s.

    Instantiation of this class bootstraps the entire application

    :ivar project: Atls Project
    :type project: AtlsProject

    """

    project_loaded = QtCore.pyqtSignal(object)

    def __init__(self, settings):
        """
        Bootstraps the Atls core logic

        :param settings: object that holds the app settings
        :type settings: AppSettings

        """
        super(AtlsCore, self).__init__()
        self.settings = settings
        self.project = None
        self.engine = Engine()

        # Initialize simulator
        self.simulator = Simulator(self._simulation_handler)

        # Time, state and other internals
        self._logger = logging.getLogger(__name__)
        #self._logger.setLevel(logging.DEBUG)

    @property
    def t_next_forecast(self):
        return self._forecast_task.run_time

    # Project handling

    def open_project(self, path):
        """
        Open ATLS project file located at path

        :param path: path to the atls project file
        :type path: str

        """
        if not os.path.exists(path):
            self._logger.error('Could not find project: ' + path)
            return
        # We add an additional / in front of the url. So now we have 3 slashes
        # in total, because host and db-name section are both empty for sqlite
        store_path = 'sqlite:///' + path
        self._logger.info('Loading project at ' + path +
                          ' - This might take a while...')
        store = Store(store_path, DataModel)
        self.project = AtlsProject(store)
        self.engine.observe_project(self.project)
        self.project_loaded.emit(self.project)
        self._logger.info('...done')

    def create_project(self, path):
        """
        Create a new project at path and load it.

        If a project exists at path, it will be replaced.

        """
        if self.project:
            self.close_project()
        if os.path.exists(path):
            os.remove(path)
        store_path = 'sqlite:///' + path
        self._logger.info('Creating project at ' + path)
        store = Store(store_path, DataModel)
        store.commit()
        store.close()
        self.open_project(path)

    def close_project(self):
        self.project.close()
        self.project = None

    # Running

    def start(self):
        if self.settings.value('enable_lab_mode'):
            self.start_simulation()
        else:
            self._logger.notice('ATLS only works in lab mode at the moment')

    def pause(self):
        if self.settings.value('enable_lab_mode'):
            self.pause_simulation()

    def stop(self):
        if self.settings.value('enable_lab_mode'):
            self.stop_simulation()

    # Simulation

    def start_simulation(self):
        """
        (Re)starts the simulation.

        Replays the events from the seismic history.

        """
        #self._profiler = Profiler()
        #self._profiler.start()
        if self.project is None:
            return
        self._logger.info('Starting simulation')
        if self.simulator.stopped:
            self._init_simulation()
        # Start simulator
        self.simulator.start()

    def _init_simulation(self):
        """
        (Re)initialize simulator and scheduler for a new simulation

        """
        # Reset task scheduler based on the first simulation step time
        time_range = self._simulation_time_range()
        inf_speed = self.settings.value('lab_mode/infinite_speed', type=bool)
        if inf_speed:
            dt_h = self.settings.value('engine/fc_interval', type=float)
            dt = timedelta(hours=dt_h)
            step_signal = self.forecast_complete
            self.simulator.configure(time_range, step_on=step_signal, dt=dt)
        else:
            speed = self.settings.value('lab_mode/speed', type=float)
            self.simulator.configure(time_range, speed=speed)

    def pause_simulation(self):
        """ Pauses the simulation. """
        self._logger.info('Pausing simulation')
        self.simulator.pause()

    def stop_simulation(self):
        """ Stops the simulation """
        self.simulator.stop()
        self._logger.info('Stopping simulation')

    def _simulation_time_range(self):
        event_time_range = self.project.event_time_range()
        start_date = self.settings.date_value('lab_mode/forecast_start')
        start_date = start_date if start_date else event_time_range[0]
        end_date = event_time_range[1]
        return start_date, end_date

    # Simulation handling

    def _simulation_handler(self, simulation_time):
        """ Invoked by the simulation whenever the project time changes """
        self.project.update_project_time(simulation_time)


