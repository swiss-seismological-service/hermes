# -*- encoding: utf-8 -*-
"""
RAMSIS Core Controller.

This module defines a single class `Controller` which acts as the
central coordinator for all core (i.e. non UI) components.

"""

import logging
from enum import Enum, auto
from PyQt5 import QtCore
from collections import namedtuple
from datetime import timedelta


from ramsis.datamodel.seismics import SeismicEvent
from ramsis.datamodel.hydraulics import HydraulicSample
from RAMSIS.core.engine.engine import Engine
from RAMSIS.core.wallclock import WallClock, WallClockMode
from RAMSIS.core.simulator import Simulator, SimulatorState
from RAMSIS.core.taskmanager import TaskManager
from RAMSIS.core.store import Store


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
        assert (launch_mode == LaunchMode.LAB), \
            f'Mode {launch_mode} is not implemented'
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
            # TODO LH: always use forecast_start
            self.clock.reset(project.settings['forecast_start'] or
                             project.starttime)
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

    def fetch_seismic_events(self):
        """
        Reload seismic catalog by fetching all events from the
        seismic data source.

        """
        self._logger.info('Re-fetching seismic data from data source')
        # TODO LH: re-add using io. A signal should be emitted when done
        #   so we can update activity messages in the gui.
        #self.seismics_data_source.fetch()
        self.project_data_changed.emit(self.project.seismiccatalog)

    def import_seismic_events(self, importer):
        """ Import seismic events manually """
        # TODO LH: re-add using io and convert wgs84 to cartesian
        try:
            events = [SeismicEvent(datetime_value=date,
                                   x_value=float(fields['lon']),
                                   y_value=float(fields['lat']),
                                   z_value=float(fields['depth']),
                                   magnitude_value=float(fields['mag']),
                                   quakeml=b'')
                      for date, fields in importer]
        except KeyError as e:
            self._logger.error('Failed to import seismic events. Make sure '
                               'the data contains lat, lon, depth, and mag '
                               'fields and that the date field has the format '
                               'dd.mm.yyyyTHH:MM:SS. The original error was ' +
                               str(e))
        else:
            # TODO LH: for some reason this is extremely slow when replacing
            #   the collection directly. Seemingly spending a lot of time
            #   in SeismicEvent.__eq__
            self.project.seismiccatalog.events = []
            self.project.seismiccatalog.events = events
            self.store.save()
        self.project_data_changed.emit(self.project.seismiccatalog)

    def fetch_hydraulic_events(self):
        """
        Reload hydraulic history by fetching all events from the
        hydraulic data source.

        """
        self._logger.info('Re-fetching hydraulic data from data source')
        hydraulics = self.project.wells[0].sections[-1].hydraulics
        # TODO LH: re-add using io. A signal should be emitted when done
        #   so we can update activity messages in the gui.
        #self.hydraulics_data_source.fetch()
        self.project_data_changed.emit(hydraulics)

    def import_hydraulics_events(self, importer):
        """ Import seismic events manually """
        # TODO LH: re-add using io. Also, we need to think of a way to
        #   specify the well/wellsection instead of hardcoding it
        try:
            samples = [HydraulicSample(datetime_value=date,
                                       bottomflow_value=float(
                                           fields.get('flow_dh') or 0),
                                       topflow_value=float(
                                           fields.get('flow_xt') or 0),
                                       bottompressure_value=float(
                                           fields.get('pr_dh') or 0),
                                       toppressure=float(
                                           fields.get('pr_xt') or 0))
                       for date, fields in importer]
        except KeyError as e:
            self._logger.error('Failed to import hydraulic events. Make sure '
                               'the .csv file contains top and bottom hole '
                               'flow and pressure fields and that the date '
                               'field has the format dd.mm.yyyyTHH:MM:SS. The '
                               'original error was ' + str(e))
        else:
            self.project.wells[0].sections[-1].hydraulics.samples = samples
            self.store.save()
        self.project_data_changed.emit(hydraulics)

    def reset_forecasts(self):
        """
        Delete forecast results and intermediate products

        This basically returns all forecasts to their 'configured but not yet
        executed' state so that the user can re-run them.

        """
        self._logger.info('Resetting all forecasts')
        for forecast in self.project.forecasts:
            forecast.reset()
        self.store.save()

    # Running

    def start(self, time_range=None, speed=1):
        """
        Start the core

        This essentially enables the task manager and with it any scheduled
        operations. If a time_range is given, the simulator will be started
        to simulate the passing of time through the time range at the speed
        given in the speed paramenter.

        :param time_range: datetime tuple indicating simulation start / end
        :param speed: simulation speed, -1 for as fast as possible

        """
        # TODO LH: implement real time operation mode
        if time_range:
            self.start_simulation(time_range, speed)
        else:
            self._logger.info('RAMSIS only works in sim mode at the moment')

    def pause(self):
        if self.simulator.state == SimulatorState.RUNNING:
            self.pause_simulation()

    def stop(self):
        if self.simulator.state == SimulatorState.RUNNING:
            self.stop_simulation()

    # Simulation

    def start_simulation(self, time_range, speed):
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
            self._init_simulation(time_range, speed)
        # Start simulator
        self.simulator.start()

    def _init_simulation(self, time_range, speed):
        """
        (Re)initialize simulator and scheduler for a new simulation

        """
        # self._logger.info(
        #     'Deleting any forecasting results from previous runs')
        # self.project.seismiccatalog.clear()
        inf_speed = True if speed == -1 else False
        if inf_speed:
            self._logger.info('Simulating at maximum speed')
            # TODO(damb): Simlation at maximum speed needs to be reimplemented.
            # There is no self.project.setting['forecast_interval'] anymore.
            # 
            #dt_h = self.project.setting['forecast_interval']
            dt_h = 6
            dt = timedelta(hours=dt_h)
            step_signal = self.engine.forecast_complete
            self.simulator.configure(time_range, step_on=step_signal, dt=dt)
        else:
            self._logger.info('Simulating at {:.0f}x'.format(speed))
            self.simulator.configure(time_range, speed=speed)
        self.task_manager.reset(time_range[0])
        self.clock.mode = WallClockMode.MANUAL
        self.clock.time = time_range[0]
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
        self.project.forecasts.append(fc)
        self.store.save()
        self.project_data_changed.emit(self.project.forecasts)
        return fc

    # TODO LH: this needs a trigger. It used to react to the settings_changed
    #   signal on project settings.
    def _on_project_settings_changed(self, _):
        self._update_data_sources()

    def _update_data_sources(self):
        pass
        # TODO LH: reimplement once daniels services are integrated
        # # Seismic
        # new_url = self.project.settings['fdsnws_url']
        # en = self.project.settings['fdsnws_enable']
        # if new_url is None:
        #     self.seismics_data_source = None
        # elif self.seismics_data_source:
        #     if self.seismics_data_source.url != new_url:
        #         self.seismics_data_source.url = new_url
        #         self._logger.info('Seismic data source changed to {}'
        #                          .format(new_url))
        #     if self.seismics_data_source.enabled != en:
        #         self.seismics_data_source.enabled = en
        #         self._logger.info('Seismic data source {}'
        #                           .format('enabled' if en else 'disabled'))
        # else:
        #     self.seismics_data_source = FDSNWSDataSource(new_url)
        #     self.seismics_data_source.enabled = en
        #     self.seismics_data_source.data_received.connect(
        #         self._on_seismic_data_received)
        # # Hydraulic
        # new_url = self.project.settings['hydws_url']
        # en = self.project.settings['hydws_enable']
        # if new_url is None:
        #     self.hydraulics_data_source = None
        # elif self.hydraulics_data_source:
        #     if self.hydraulics_data_source.url != new_url:
        #         self.hydraulics_data_source.url = new_url
        #         self._logger.info('Hydraulic data source changed to {}'
        #                           .format(new_url))
        #     if self.hydraulics_data_source.enabled != en:
        #         self.hydraulics_data_source.enabled = en
        #         self._logger.info('Hydraulic data source {}'
        #                           .format('enabled' if en else 'disabled'))
        # else:
        #     self.hydraulics_data_source = HYDWSDataSource(new_url)
        #     self.hydraulics_data_source.enabled = en
        #     self.hydraulics_data_source.data_received.connect(
        #         self._on_hydraulic_data_received)

    def _on_seismic_data_received(self, result):
        if result is not None:
            tr = result['time_range']
            importer = result['importer']
            self.project.seismiccatalog.clear_events(tr)
            self.project.seismiccatalog.import_events(importer)
            self.project.store.commit()

    def _on_hydraulic_data_received(self, result):
        if result is not None:
            tr = result['time_range']
            importer = result['importer']
            self.project.injection_history.clear_events(tr)
            self.project.injection_history.import_events(importer)
            self.project.store.commit()
