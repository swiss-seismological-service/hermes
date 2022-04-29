# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Simulator facilities
"""

import logging
from datetime import timedelta

from PyQt5 import QtCore


class SimulatorState:
    STOPPED = 0
    RUNNING = 1
    PAUSED = 2


class Simulator(QtCore.QObject):
    """
    Simulates the advancement of time over a specified time range

    The simulator works with an internal timer to simulate a time step after
    the number of milliseconds set in *step_time* has passed.
    """
    SIMULATION_INTERVAL = 900  # simulate a time step every X ms

    # Signals
    state_changed = QtCore.pyqtSignal(int)

    def __init__(self, handler):
        """
        :param callable handler: Callable that is called on each simulation
            step with the current simulation time.
        """
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self._handler = handler

        self._simulation_time = 0
        self._start_time_range = None
        self._end_time_range = None
        self._speed = 1000

        self._timer = QtCore.QTimer()
        self._state = SimulatorState.STOPPED
        self._timer.timeout.connect(self._simulate_time_step)

    @property
    def simulation_time(self):
        return self._simulation_time

    @property
    def time_range(self):
        return [self._start_time_range, self._end_time_range]

    @property
    def state(self):
        return self._state

    def configure(self, start_time_range, end_time_range, speed=1000):
        """
        Configures the simulator.

        :param list[datetime] time_range: Simulation time range (start and
            end time)
        :param float speed: simulation speed multiplier (real time = 1).
            Ignored if step_on is specified.
        """
        self._speed = speed
        self._start_time_range = start_time_range
        self._end_time_range = end_time_range

    def start_realtime(self, time_now):
        """
        Starts the simulation at start of the simulation time range

        If invoked after `pause`, the simulation is continued from where it
        stopped. The first time step is scheduled to execute immediately.

        """
        self._start_range_time = time_now
        self._simulation_time = time_now
        self._transition_to_state(SimulatorState.RUNNING)
        self._timer.start(self.SIMULATION_INTERVAL)

    def start(self):
        """
        Starts the simulation at start of the simulation time range

        If invoked after `pause`, the simulation is continued from where it
        stopped. The first time step is scheduled to execute immediately.

        """
        assert self._start_time_range is not None, \
            'Set a time range before simulating'
        if self.state != SimulatorState.PAUSED:
            self._simulation_time = self._start_time_range
        self._transition_to_state(SimulatorState.RUNNING)
        self._timer.start(self.SIMULATION_INTERVAL)

    def pause(self):
        """ Pauses the simulation. """
        self._timer.stop()
        self._transition_to_state(SimulatorState.PAUSED)

    def stop(self):
        """ Stops the simulation. """
        self._timer.stop()
        self._transition_to_state(SimulatorState.STOPPED)

    def _simulate_time_step(self):
        # skip any spurious events on start stop
        if self.state != SimulatorState.RUNNING:
            return

        simulation_ended = False
        seconds = self.SIMULATION_INTERVAL / 1000.0 * self._speed
        dt = timedelta(seconds=seconds)
        self._simulation_time += dt

        if self._end_time_range:
            if self._simulation_time >= self._end_time_range:
                simulation_ended = True

        self._handler(self._simulation_time)

        if simulation_ended:
            self.stop()

    # State transitions

    def _transition_to_state(self, state):
        self._state = state
        self.state_changed.emit(state)
