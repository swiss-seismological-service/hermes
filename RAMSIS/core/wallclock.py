# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Keeper of time

The wall clock keeps the current time, real or simulated, and emits a signal
whenever the time has advanced significantly.
"""

from enum import Enum, auto
from datetime import timedelta, datetime
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class WallClockMode(Enum):
    """ Wall clock operation mode """
    REAL_TIME = auto()  #: In real time mode the wall clock follows system time
    MANUAL = auto()     #: In manual mode the time must be set manually


_RT_RESOLUTION = 200  # Internal resolution for real time operation in ms


class WallClock(QObject):
    """
    Keeps the current time.

    The wall clock keeps track of absolute time. This can either be the local
    system time for real time operations or a simulated absolute time for
    real time simulations.

    If the wall clock is armed, the time_changed signal will be emitted
    whenever the time set in :attribute:`resolution` (or more) has passed.

    .. note:: The wall clock does not try to be extremely accurate. It should
        probably not be used with << 1s resolution.

    """

    #: pyqtSignal emitted whenever the wall clock time changes, carries time.
    time_changed = pyqtSignal(object)

    def __init__(self, mode=WallClockMode.MANUAL, resolution=None):
        """
        WallClock initializer

        :param WallClockMode mode: Initial mode. The default is
            :attribute:`WallClockMode.MANUAL` for manual operation.
        :param datetime.datetime initial: Initial time. The default is the
            current system time at the time of initialization.
        :param datetime.timedelta resolution: Time resolution. The default is
            one second. The `time_changed` signal is emitted whenever more than
            `resolution` time has passed since the last emission.
        :param args: Additional positional arguments passed through to QObject
        :param kwargs: Additional keyword arguments passed through to QObject
        """
        super().__init__()
        self.resolution = resolution or timedelta(seconds=1)
        self._time = datetime.utcnow()
        self._rt_update_timer = QTimer()
        self._rt_update_timer.timeout.connect(self._on_rt_timer_timout)
        self.armed = False
        self._mode = mode

    def start_realtime(self, time_now):
        self.mode = WallClockMode.REAL_TIME
        self._time = time_now
        self.arm()

    @property
    def time(self):
        """ Returns the current wall clock time """
        return self._time

    @time.setter
    def time(self, time):
        """
        Set the current wall clock time to `time`.

        If the new time is > :attribute:`time` + :attribute:`resolution` the
        :attribute:`time_changed` signal will be emitted.

        :param datetime.datetime time: The new time.
        """
        emit = self.armed and time >= self._time + self.resolution
        if emit:
            self._time = time
            self.time_changed.emit(self._time)

    @property
    def mode(self):
        """
        The current run :class:`WallClockMode`.

        .. note:: Setting a new mode disarms the clock.
        """
        return self._mode

    @mode.setter
    def mode(self, mode):
        if mode == self._mode:
            return
        self.disarm()
        if mode == WallClockMode.REAL_TIME:
            self._rt_update_timer.start(_RT_RESOLUTION)
        elif mode == WallClockMode.MANUAL:
            self._rt_update_timer.stop()

    def arm(self):
        """ Start emitting :attribute:`time_changed` """
        self.armed = True

    def disarm(self):
        """ Stop emitting :attribute:`time_changed` """
        self.armed = False

    def reset(self, time):
        """
        Reset wall clock

        Disarms the clock, sets the mode back to
        :attribute:`manual <WallClockMode.MANUAL>` mode and resets the time to
        the time given as an argument.

        :param datetime time: Time (and date) after reset.

        """
        self.disarm()
        self.mode = WallClockMode.MANUAL
        self._time = time

    def _on_rt_timer_timout(self):
        self.time = datetime.utcnow()
