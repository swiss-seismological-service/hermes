# -*- encoding: utf-8 -*-
"""
Simulates forecasting

Simulates incoming seismic events and triggers updates on the forecast
    
"""

from model.seismiceventhistory import SeismicEventHistory
from PyQt4.QtCore import QTimer
from datetime import timedelta


class Simulator(object):
    """Seismic event simulator

    Simulates seismic events from an existing history at the speed of
    step_time/speed
    :ivar speed: Speed factor for simulation
    :ivar step_time: Simulation step time in seconds

    """

    def __init__(self, event_history, handler):
        """
        :param event_history: history of seismic events
        :type event_history: SeismicEventHistory
        :param handler: function that is called on each simulation step
            The handler function must accept three arguments:
            handler(time, event_occurred, done), where *time* is a
            date time object that contains the current simulation time,
            *event_occurred* is True if an event occurred during the last
            simulation step and *done* is True if this was the last simulation
            step.

        """

        self._event_history = event_history
        self._handler = handler

        self._history_iterator = None
        self._next_event = None
        self._simulation_time = 0
        self.step_time = 1
        self.speed = 1

        self._timer = QTimer()
        self._stopped = False
        self._paused = False
        self._timer.timeout.connect(self._step)

    def start(self):
        """Starts the simulation at the time of the first event in the
        catalog.

        """
        if not self._paused:
            first_event = self._event_history[0]
            self._history_iterator = iter(self._event_history)
            self._simulation_time = first_event.date_time
            self._next_event = self._history_iterator.next()
            self._stopped = False
        self._paused = False
        self._timer.singleShot(float(self.step_time) / self.speed * 1000,
                               self._step)

    def pause(self):
        """ Pauses the simulation. Unpause with start. """
        self._paused = True
        self._timer.stop()

    def stop(self):
        """ Stops the simulation"""
        self._paused = False
        self._stopped = True

    def _step(self):

        # skip any spurious events on start stop
        if self._paused or self._stopped:
            return

        event_occurred = False
        simulation_ended = False
        self._simulation_time += timedelta(seconds=self.step_time)

        # check if one or more event occurred during the simulation step
        while self._next_event and \
                self._next_event.date_time < self._simulation_time:
            event_occurred = True
            try:
                self._next_event = self._history_iterator.next()
            except:
                self._next_event = None

        if self._next_event is None:
            simulation_ended = True

        self._handler(self._simulation_time, event_occurred, simulation_ended)

        if not simulation_ended:
            self._timer.singleShot(float(self.step_time) / self.speed * 1000,
                                   self._step)

