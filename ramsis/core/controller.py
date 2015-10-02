# -*- encoding: utf-8 -*-
"""
RAMSIS Core Controller.

This module defines a single class `Controller` which acts as the
central coordinator for all core components.

"""

import logging
from datetime import timedelta
import os

from PyQt4 import QtCore

from data.project.store import Store
from data.project.ramsisproject import RamsisProject
from data.ormbase import OrmBase
from simulator import Simulator, SimulatorState
from core.engine import Engine
import core.ismodelcontrol as mc


# from tools import Profiler


class Controller(QtCore.QObject):
    """
    RT-RAMSIS Core Controller Class

    A singleton instance of `Controller` is created when the program
    launches. The `Controller` is responsible for setting up and connecting
    all other core components, so it effectively bootstraps the application
    logic.

    During run time, the `Controller` acts as the central entry point for
    the user interface.

    :ivar RamsisProject project: Currently loaded project
    :param AppSettings settings: reference to the application settings

    """

    project_loaded = QtCore.pyqtSignal(object)

    def __init__(self, settings):
        super(Controller, self).__init__()
        self._settings = settings
        self.project = None
        self.engine = Engine(settings)

        # Load active IS models
        mc.load_models(self._settings.value('ISHA/models'))

        # Initialize simulator
        self.simulator = Simulator(self._simulation_handler)

        # Time, state and other internals
        self._logger = logging.getLogger(__name__)
        # self._logger.setLevel(logging.DEBUG)

    # Project handling

    def open_project(self, path):
        """
        Open RAMSIS project file located at path

        :param str path: path to the ramsis project file

        """
        if not os.path.exists(path):
            self._logger.error('Could not find project: ' + path)
            return
        # We add an additional / in front of the url. So now we have 3 slashes
        # in total, because host and db-name section are both empty for sqlite
        store_path = 'sqlite:///' + path
        self._logger.info('Loading project at ' + path +
                          ' - This might take a while...')
        store = Store(store_path, OrmBase)
        self.project = RamsisProject(store, os.path.basename(path))
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
        store = Store(store_path, OrmBase)
        store.commit()
        store.close()
        self.open_project(path)

    def close_project(self):
        """
        Close the current project.

        """
        self.project.close()
        self.project = None

    # Running

    def start(self):
        if self._settings.value('enable_lab_mode'):
            self.start_simulation()
        else:
            self._logger.notice('RAMSIS only works in lab mode at the moment')

    def pause(self):
        if self._settings.value('enable_lab_mode'):
            self.pause_simulation()

    def stop(self):
        if self._settings.value('enable_lab_mode'):
            self.stop_simulation()

    # Simulation

    def start_simulation(self):
        """
        Starts the simulation.

        The simulation replays the events from the seismic and hydraulic
        histories at the simulation speed that is currently configured and
        triggers forecasts and other computations at the appropriate times.
        See :doc:`core` documentation for further information on how simulation
        works.

        If the simulation was previously paused by `pause_simulation` the
        simulation will simply continue. Otherwise, the simulator will be
        reset to the start of its :meth:`configured
        <core.simulator.Simulator.configure>` time range and begin from there.

        """
        # self._profiler = Profiler()
        # self._profiler.start()
        if self.project is None:
            return
        self._logger.info('Starting simulation')
        if self.simulator.state == SimulatorState.STOPPED:
            self._init_simulation()
        # Start simulator
        self.simulator.start()

    def _init_simulation(self):
        """
        (Re)initialize simulator and scheduler for a new simulation

        """
        self._logger.info(
            'Deleting any forecasting results from previous runs')
        self.project.forecast_history.clear()
        # Reset task scheduler based on the first simulation step time
        time_range = self._simulation_time_range()
        inf_speed = self._settings.value('lab_mode/infinite_speed')
        if inf_speed:
            self._logger.info('Simulating at maximum speed')
            dt_h = self._settings.value('engine/fc_interval')
            dt = timedelta(hours=dt_h)
            step_signal = self.engine.forecast_complete
            self.simulator.configure(time_range, step_on=step_signal, dt=dt)
        else:
            speed = self._settings.value('lab_mode/speed')
            self._logger.info('Simulating at {:.0f}x'.format(speed))
            self.simulator.configure(time_range, speed=speed)
        self.engine.reset(time_range[0])

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
        start_date = self._settings.date_value('lab_mode/forecast_start')
        start_date = start_date if start_date else event_time_range[0]
        end_date = event_time_range[1]
        return start_date, end_date

    # Simulation handling

    def _simulation_handler(self, simulation_time):
        """ Invoked by the simulation whenever the project time changes """
        self.project.update_project_time(simulation_time)
