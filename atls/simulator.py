# -*- encoding: utf-8 -*-
"""
Simulates forecasting

Simulates incoming seismic events and triggers updates on the forecast
    
"""

from PyQt4 import QtCore
from datetime import timedelta
import logging


class SimulatorState:
    STOPPED = 0
    RUNNING = 1
    PAUSED = 2


class Simulator(QtCore.QObject):
    """
    Simulates the advancement of time over a specified time range

    The simulator works with an internal timer to simulate a time step after
    the number of milliseconds set in *step_time* has passed. Alternatively,
    an external pyqt signal can be used to trigger time steps which must be
    set by calling step_on_external_signal.

    """

    # Signals
    state_changed = QtCore.pyqtSignal(int)

    def __init__(self, handler):
        """
        :param handler: function that is called on each simulation step
            with the current simulation time.

        """
        super(Simulator, self).__init__()
        self.simulation_interval = 200  # simulate a time step every X ms
        self._speed = 1000

        self._handler = handler
        self._simulation_time = 0
        self._logger = logging.getLogger(__name__)
        self._time_range = None

        self._timer = QtCore.QTimer()
        self._state = SimulatorState.STOPPED
        self._timer.timeout.connect(self._simulate_time_step)

        # these are used when simulating on an external signal instead of the
        # internal timer
        self._external_signal = None
        self._dt = None

    @property
    def simulation_time(self):
        return self._simulation_time

    @property
    def speed(self):
        return self._speed

    @property
    def state(self):
        return self._state

    def configure(self, time_range, speed=1000, step_on=None, dt=None):
        """
        Configures the simulator.

        :param time_range: Simulation time range (start and end time)
        :type time_range: list[datetime]
        :param speed: simulation speed multiplier (real time = 1). Ignored if
            step_on is used.
        :type speed: float
        :param step_on: Signal the simulator uses to advance time by dt. If
            not set an internal timer is used and dt is ignored.
        :type step_on: QtCore.QSignal
        :param dt: Time step when step signal is used
        :type dt: datetime

        """
        self._speed = speed
        self._time_range = time_range
        self._external_signal = step_on
        self._dt = dt

    def step_on_internal_timer(self):
        """
        Configures the simulator to run on the internal timer.

        This is the default.

        """
        self._dt = None
        if self._external_signal:
            self._external_signal.disconnect(self._simulate_time_step)
        self._external_signal = None

    def step_on_external_signal(self, step_signal, dt):
        """
        Configures the simulator to run on an external signal.

        The simulator listens to the *step_signal* and increases the project
        time by dt whenever the signal is received. The simulator connects to
        the signal via a queue to make sure the run loop can return before the
        next iteration executes.
        The first step is executed immediately upon start()

        :param step_signal: signal on which to simulate a time step
        :type step_signal: pyqt signal
        :param dt: time step
        :type dt: timedelta

        """
        self._dt = dt
        self._external_signal = step_signal
        self._external_signal.connect(self._simulate_time_step,
                                      type=QtCore.Qt.QueuedConnection)

    def start(self):
        """
        Starts the simulation at start of the simulation time range

        If invoked after *pause*, the simulation is continued from where it
        stopped. The first time step is scheduled to execute immediately.

        """
        assert self._time_range is not None, 'Set a time range before simulating'
        if self.state != SimulatorState.PAUSED:
            self._simulation_time = self._time_range[0]
        self._transition_to_state(SimulatorState.RUNNING)
        if self._external_signal:
            # Execute first step immediately after run loop returns
            QtCore.QTimer.singleShot(0, self._simulate_time_step)
        else:
            self._timer.start(self.simulation_interval)

    def pause(self):
        """ Pauses the simulation. Unpause with start. """
        if self._external_signal is None:
            self._timer.stop()
        self._transition_to_state(SimulatorState.PAUSED)

    def stop(self):
        """ Stops the simulation"""
        if self._external_signal is None:
            self._timer.stop()
        else:
            self._external_signal.disconnect(self._simulate_time_step)
            self._external_signal = None
            self._dt = None
        self._transition_to_state(SimulatorState.STOPPED)

    def _simulate_time_step(self):
        # skip any spurious events on start stop
        if self.state != SimulatorState.RUNNING:
            return

        simulation_ended = False
        if self._external_signal is None:
            dt = timedelta(seconds=self.simulation_interval / 1000.0
                                   * self.speed)
        else:
            dt = self._dt
        self._simulation_time += dt

        if self._simulation_time >= self._time_range[1]:
            simulation_ended = True

        self._handler(self._simulation_time)

        if simulation_ended:
            self.stop()

    # State transitions

    def _transition_to_state(self, state):
        self._state = state
        self.state_changed.emit(state)