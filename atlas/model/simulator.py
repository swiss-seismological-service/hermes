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

    @property
    def simulation_time(self):
        return self._simulation_time

    def start(self):
        """Starts the simulation at the time of the first event in the
        catalog.

        """
        if self.time_range is None:
            self._logger.warning('Attempted to start simulator without setting'
                                 'a time range.')
            return

        if not self._paused:
            self._simulation_time = self.time_range[0]
            self._stopped = False
        self._paused = False
        self._timer.start(self.step_time)

    def pause(self):
        """ Pauses the simulation. Unpause with start. """
        self._paused = True
        self._timer.stop()

    def stop(self):
        """ Stops the simulation"""
        self._paused = False
        self._stopped = True
        self._timer.stop()

    def _do_step(self):
        # skip any spurious events on start stop
        if self._paused or self._stopped:
            return

        simulation_ended = False
        dt = self.step_time * self.speed / 1000
        self._simulation_time += timedelta(seconds=dt)

        if self._simulation_time >= self.time_range[1]:
            simulation_ended = True

        self._handler(self._simulation_time)

        if simulation_ended:
            self.stop()

