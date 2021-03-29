# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
RAMSIS Core Controller.

This module defines a single class `Controller` which acts as the
central coordinator for all core (i.e. non UI) components.
"""

import logging

from datetime import datetime
from enum import Enum
from operator import attrgetter

from PyQt5 import QtCore
from collections import namedtuple

from RAMSIS.core.engine.engine import Engine
from RAMSIS.core.wallclock import WallClock, WallClockMode
from RAMSIS.core.simulator import Simulator, SimulatorState
from RAMSIS.core.taskmanager import TaskManager
from RAMSIS.core.store import Store
from RAMSIS.core.datasources import FDSNWSDataSource, HYDWSDataSource

WGS84_EPSG = 4326


TaskRunInfo = namedtuple('TaskRunInfo', 't_project')
"""
Used internally to pass information to repeating tasks
t_project is the project time at which the task is launched

"""


class LaunchMode(Enum):
    """
    Application Mode

    The application can launch in one of two modes.

    """
    REAL_TIME = 'real-time'  #: Real time operation for live applications
    LAB = 'lab'  #: Lab mode where the user simulates through recorded data


class Controller(QtCore.QObject):
    """
    RT-RAMSIS Core Controller Class

    A singleton instance of `Controller` is created when the program
    launches. The `Controller` is responsible for setting up and connecting
    all other core components, so it effectively bootstraps the application
    logic.

    At run time, the `Controller` acts as the central entry point for
    the user interface.

    :ivar Project project: Currently loaded project
    :param RAMSIS.application.Application app: reference to the application
        top level object

    """

    #: Signal emitted after a new project has been loaded into the core
    project_loaded = QtCore.pyqtSignal(object)
    #: Signal emitted when the currently active project is about to be closed
    project_will_unload = QtCore.pyqtSignal()
    #: Signal emitted when a data base connection is established or closed
    store_changed = QtCore.pyqtSignal()
    #: Signal emitted when project data changes. Carries the changed instance
    # TODO LH: This is a cheap and unsatisfactory replacement for the change
    #   signals that model objects used to emit and that were caught by the
    #   GUI to update views. We might need a better solution here. I tried
    #   listening to SQLAlchemy events but there is too little control over the
    #   granularity of events. Best would probably still be for data model
    #   objects to emit change signals somehow.
    project_data_changed = QtCore.pyqtSignal(object)

    def __init__(self, app, launch_mode):
        super(Controller, self).__init__()
        self._settings = app.app_settings
        self._launch_mode = launch_mode
        self.store = None
        self.project = None
        self.fdsnws_previous_end_time = None
        self.hydws_previous_end_time = None
        self.seismics_data_source = None
        self.hydraulics_data_source = None

        # Core components for real time and simulation operation
        self.engine = Engine(self)
        self.clock = WallClock()
        self.external_proj = WGS84_EPSG

        # Save time range and speed of the simulator
        self.start_time_range = None
        self.end_time_range = None
        self.speed = 1000

        def simulation_handler(time):
            self.clock.time = time

        self.simulator = Simulator(simulation_handler)
        self.task_manager = TaskManager(core=self)

        # Other internals
        self._logger = logging.getLogger(__name__)
        # self._logger.setLevel(logging.DEBUG)

        # Signals
        app.app_launched.connect(self._on_app_launched)

    # DB handling

    @property
    def launch_mode(self):
        return self._launch_mode

    def connect(self, db_url):
        """
        Connect to a new data store

        :param str db_url: Fully qualified db url to connect to (including
            user, pw)
        :return: True if connection is successful, False otherwise
        :rtype: Bool

        """
        self.disconnect()
        store = Store(db_url)
        if store.test_connection():
            self.store = store
            self.store_changed.emit()
            return True
        return False

    def disconnect(self):
        """ Disconnect from the current data store """
        if self.project:
            self.close_project()
        if self.store:
            self.store.close()
            self.store = None
            self.store_changed.emit()

    # Project handling

    def open_project(self, project):
        """
        Open RAMSIS project

        This makes `project` the cores currently active project and
        reconfigures tasks based on the project's timeline. In Lab Mode
        it also resets the wall clock to the start of the project.

        :param project: Project to load
        :type project: ramsis.datamodel.project.Project

        """

        self._logger.info(f'Loading project {project.name}')
        if self.project:
            self.close_project()
        self.project = project

        if self.launch_mode == LaunchMode.LAB:
            try:
                self.start_time_range = min(
                    project.forecast_iter(),
                    key=attrgetter('starttime')).starttime
            except ValueError:
                self._logger.warning(
                    'No forecasts configured. Use project starttime: '
                    f'{project.starttime}.')
                self.start_time_range = project.starttime
            self.clock.reset(self.start_time_range)
        elif self.launch_mode == LaunchMode.REAL_TIME:
            # sarsonl perhaps update to get datetime from another source
            # I think this is a dummy variable to set time graphically
            time_now = datetime.utcnow()
            self.clock.start_realtime(time_now)
            self.start_realtime(time_now)
        self.project_loaded.emit(project)
        self._update_data_sources()
        self._logger.info('... done loading project')

    def close_project(self):
        """
        Close the currently active project.

        """
        self._logger.info(f'Closing project {self.project.name}')
        self.project_will_unload.emit()
        self.project = None

    def update_project(self, obj, mapping={}):
        """
        Update an project's object from a mapping.

        :param obj: Object to be updated
        :param dict mapping: Mapping to be used to update the object's values
        """
        for k, v in mapping.items():
            attr = getattr(obj, k, None)
            if attr and attr != v:
                setattr(obj, k, v)

        self.store.save()
        self.project_data_changed.emit(obj)

    # Other user actions

    def start(self, time_range=None, speed=1.0):
        """
        Start the core

        This essentially enables the task manager and with it any scheduled
        operations. If a LAB mode, the simulator will be started
        to simulate the passing of time through the time range at the speed
        given in the speed paramenter.
        Otherwise, a realtime simulation will be started.

        :param time_range: datetime tuple indicating simulation start / end
        :param speed: simulation speed, -1 for as fast as possible

        """
        if self.launch_mode == LaunchMode.LAB:
            if not time_range:
                try:
                    start = min(self.project.forecast_iter(),
                                key=attrgetter('starttime')).starttime
                except ValueError:
                    self._logger.warning(
                        'No forecasts configured. Use project starttime: '
                        f'{self.project.starttime}.')
                    start = self.project.starttime
                finally:
                    # TODO decide if this is appropriate
                    # Would we ever want a simulation to continue beyond
                    # this time?
                    end = datetime.utcnow()
            else:
                start_pyqt, end_pyqt = time_range
                start = start_pyqt.toPyDateTime()
                end = end_pyqt.toPyDateTime()
            if speed == 1.0:
                speed = self._settings['simulation']['speed']
            self.start_time_range = start
            self.end_time_range = end
            self.speed = speed
            self.start_simulation()
        else:
            self._logger.info('Trying to start RAMSIS in real-time mode.')
            self.start_realtime(datetime.utcnow())

    def pause(self):
        if self.simulator.state == SimulatorState.RUNNING:
            self.pause_simulation()

    def stop(self):
        if self.simulator.state == SimulatorState.RUNNING:
            self.stop_simulation()

    def start_realtime(self, time_now):

        if self.project is None:
            return
        self._logger.info(f'Starting realtime operation at {time_now}')
        self._init_realtime(time_now)
        self.simulator.configure(None, None, speed=1.0)
        self.simulator.start_realtime(time_now)

    def _init_realtime(self, time_now):
        self.task_manager.reset(time_now)
        self.clock.mode = WallClockMode.REAL_TIME
        self.clock.time = time_now
        self.clock.arm()

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
        self._logger.info('Simulating at {:.0f}x'.format(self.speed))
        self.simulator.configure(self.start_time_range,
                                 self.end_time_range,
                                 speed=self.speed)

        self.task_manager.reset(self.start_time_range)
        self.clock.mode = WallClockMode.MANUAL
        self.clock.time = self.start_time_range
        self.clock.arm()

    def pause_simulation(self):
        """ Pauses the simulation. """
        self._logger.info('Pausing simulation')
        self.simulator.pause()

    def stop_simulation(self):
        """
        Stops the simulation.

        All seismic and hydraulic events are cleared from the database.

        """
        self._logger.info('Stopping simulation')
        self.simulator.stop()
        self._init_simulation()

    # Signal slots

    def _on_app_launched(self):
        """ Invoked when the application has launched """
        db_settings = self._settings['database']
        if all(v for v, k in db_settings.items()):
            protocol, address = db_settings['url'].split('://')
            self._logger.info(f'Reconnecting to {address}/'
                              f'{db_settings["name"]}')
            db_url = f'{protocol}://{db_settings["user"]}:' \
                f'{db_settings["password"]}@{address}/{db_settings["name"]}'
            self.connect(db_url)

    # Forecast handling

    def add_forecast(self, fc):
        """
        Add a forecast.

        :param fc: Forecast to be added.
        :type fc: :py:class:`ramsis.datamodel.forecast.Forecast`
        """

        self.project = self.store.get_fresh(self.project)
        self.project.forecasts.append(fc)
        self.store.save()
        self.project_data_changed.emit(self.project.forecasts)
        return fc

    # TODO LH: this needs a trigger. It used to react to the settings_changed
    #   signal on project settings.
    def _on_project_settings_changed(self, _):
        self._update_data_sources()

    def _update_data_sources(self):
        try:
            enabled = self.project.settings['fdsnws_enable']
            url = self.project.settings['fdsnws_url']
        except KeyError as err:
            self._logger.warning(
                f'Invalid project configuration: {err}')
        else:
            if url is None:
                self.seismics_data_source = None
            elif self.seismics_data_source:
                if self.seismics_data_source.url != url:
                    self.seismics_data_source.url = url
                    self._logger.info(
                        f'fdsnws-event changed to {url}.')
                if self.seismics_data_source.enabled != enabled:
                    self.seismics_data_source.enabled = enabled
                    self._logger.info(
                        'fdsnws-event {}.'.format(
                            'enabled' if enabled else 'disabled'))
            else:
                self.seismics_data_source = FDSNWSDataSource(
                    url, timeout=None, project=self.project)
                self.seismics_data_source.enabled = enabled
                self.seismics_data_source.data_received.connect(
                    self._on_seismic_data_received)

        try:
            enabled = self.project.settings['hydws_enable']
            url = self.project.settings['hydws_url']
        except KeyError as err:
            self._logger.warning(
                f'Invalid project configuration: {err}')
        else:
            # XXX(damb): Borehole is specified in the hydws URL; for
            # multiple boreholes add a list of borehole identifiers
            if url is None:
                self.hydraulics_data_source = None
            elif self.hydraulics_data_source:
                if self.hydraulics_data_source.url != url:
                    self.hydraulics_data_source.url = url
                    self._logger.info(
                        f'hydws changed to {url}.')
                if self.hydraulics_data_source.enabled != enabled:
                    self.hydraulics_data_source.enabled = enabled
                    self._logger.info(
                        'hydws {}'.format(
                            'enabled' if enabled else 'disabled'))
            else:
                self.hydraulics_data_source = HYDWSDataSource(
                    url, timeout=None, project=self.project)
                self.hydraulics_data_source.enabled = enabled
                self.hydraulics_data_source.data_received.connect(
                    self._on_hydraulic_data_received)

    def _on_seismic_data_received(self, cat):
        if cat is not None:
            self.project.seismiccatalog = cat

            self.store.save()

            self._logger.debug(
                f'Project seismic data ({self.project.seismiccatalog}).')
            self.project_data_changed.emit(self.project.seismiccatalog)

    def _on_hydraulic_data_received(self, well):
        if well is not None:
            self.project.well = well
            well_project = self.project.well

            self.store.save()
            if well_project and well_project.sections:
                msg = ('Project borehole data '
                       f'(sections={len(well_project.sections)}')
                if well_project.sections[0].hydraulics:
                    msg += (', samples='
                            f'{len(well_project.sections[0].hydraulics)}')
                msg += ').'

                self._logger.debug(msg)

            self.project_data_changed.emit(well_project)
