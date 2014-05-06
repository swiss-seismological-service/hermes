# -*- encoding: utf-8 -*-
"""
Simulates forecasting

Simulates incoming seismic events and triggers updates on the forecast
    
"""

from PyQt4.QtCore import QTimer, Qt
from datetime import timedelta
import logging


class Simulator(object):
    """
    Simulates the advancement of time over a specified time range

    The simulator works with an internal timer to simulate a time step after
    the number of milliseconds set in *step_time* has passed. Alternatively,
    an external pyqt signal can be used to trigger time steps which must be
    set by calling step_on_external_signal.


    """

    def __init__(self, handler):
        """
        :param handler: function that is called on each simulation step
            with the current simulation time.

        """
        self.simulation_interval = 200  # simulate a time step every X ms
        self.speed = 1000

        self._handler = handler
        self._simulation_time = 0
        self._logger = logging.getLogger(__name__)

        self._timer = QTimer()
        self._stopped = False
        self._paused = False
        self._timer.timeout.connect(self._simulate_time_step)

        # these are used when simulating on an external signal instead of the
        # internal timer
        self._external_signal = None
        self._dt = None

    @property
    def simulation_time(self):
        return self._simulation_time

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
                                      type=Qt.QueuedConnection)

    def start(self):
        """
        Starts the simulation at start of the simulation time range

        If invoked after *pause*, the simulation is continued from where it
        stopped. The first time step is scheduled to execute immediately.

        """
        assert self.time_range is not None, 'Set a time range before simulating'
        if not self._paused:
            self._simulation_time = self.time_range[0]
        self._stopped = False
        self._paused = False
        if self._external_signal:
            # Execute first step immediately after run loop returns
            QTimer.singleShot(0, self._simulate_time_step)
        else:
            self._timer.start(self.simulation_interval)

    def pause(self):
        """ Pauses the simulation. Unpause with start. """
        self._paused = True
        if self._external_signal is None:
            self._timer.stop()

    def stop(self):
        """ Stops the simulation"""
        self._paused = False
        self._stopped = True
        if self._external_signal is None:
            self._timer.stop()
        else:
            self._external_signal.disconnect(self._simulate_time_step)
            self._external_signal = None
            self._dt = None

    def _simulate_time_step(self):
        # skip any spurious events on start stop
        if self._paused or self._stopped:
            return

        simulation_ended = False
        if self._external_signal is None:
            dt = timedelta(seconds=self.simulation_interval / 1000.0
                                   * self.speed)
        else:
            dt = self._dt
        self._simulation_time += dt

        if self._simulation_time >= self.time_range[1]:
            simulation_ended = True

        self._handler(self._simulation_time)

        if simulation_ended:
            self.stop()