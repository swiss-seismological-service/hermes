# -*- encoding: utf-8 -*-
"""
Simulates forecasting

Simulates incoming seismic events and triggers updates on the forecast
    
"""

from PyQt4.QtCore import QTimer
from datetime import timedelta
import logging


class Simulator(object):
    """
    Simulates the advancement of time over a specified time range

    """

    def __init__(self, handler):
        """
        :param handler: function that is called on each simulation step
            with the current simulation time.

        """
        self.step_time = 200            # simulation step in ms
        self.speed = 1000
        self.time_range = None          # start and end time of the simulation

        self._handler = handler
        self._simulation_time = 0
        self._logger = logging.getLogger(__name__)

        self._timer = QTimer()
        self._stopped = False
        self._paused = False
        self._timer.timeout.connect(self._do_step)

        # these are used when simulating on an external signal instead of the
        # internal timer
        self._external_signal = None
        self._dt = None

    @property
    def simulation_time(self):
        return self._simulation_time

    def start(self):
        """
        Starts the simulation at start of the simulation time range

        """
        assert self.time_range is not None, 'Set a time range before simulating'
        if not self._paused:
            self._simulation_time = self.time_range[0]
            self._stopped = False
        self._paused = False
        self._timer.start(self.step_time)

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
            self._external_signal.disconnect(self._do_step)
            self._external_signal = None
            self._dt = None

    def start_on_external_signal(self, step_signal, dt):
        """
        Runs the simulator on an external signal.

        The simulator listens to the *step_signal* and increases the project
        time by dt whenever the signal is received. The first step is executed
        immediately

        :param step_signal: signal on which to simulate a time step
        :type step_signal: pyqt signal
        :param dt: time step
        :type dt: timedelta

        """
        assert self.time_range is not None, 'Set a time range before simulating'
        self._dt = dt
        self._external_signal = step_signal
        self._external_signal.connect(self._do_step)
        self._simulation_time = self.time_range[0] + dt
        self._handler(self._simulation_time)

    def _do_step(self):
        # skip any spurious events on start stop
        if self._paused or self._stopped:
            return

        simulation_ended = False
        if self._external_signal is None:
            dt = timedelta(seconds=self.step_time * self.speed / 1000)
        else:
            dt = self._dt
        self._simulation_time += dt

        if self._simulation_time >= self.time_range[1]:
            simulation_ended = True

        self._handler(self._simulation_time)

        if simulation_ended:
            self.stop()

