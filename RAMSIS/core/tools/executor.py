# Copyright (c) 2019, ETH Zurich, Swiss Seismological Service
"""
Executors manage queues to kick off asynchronous tasks using a Qt run loop.
This module only provides base classes for concrete Executor implementations.

There are three types of Executors:

- Simple: Simple Executor that starts an asynchronous task and emits the
  :cvar:`_Executor.status_changed` message when the underlying task has
  changed its execution status.
- Parallel: Starts a series of child Executors and emits a `status_changed`
  signal with a :cvar:`~ExecutionStatus.Status.SUCCESS` status once all
  children have completed successfully.
- Serial: Starts the first child Executor and waits for it to report
  completion via :cvar:`~_Executor.status_changed` signal before starting the
  next one. Emits :cvar:`~ExecutionStatus.Status.SUCCESS` after the last child
  has finished.

Combining the three classes above, users can implement execution chains with
complex dependencies.

.. note::
   Executors don't implement any kind of concurrency themselves. They expect
   their run implementations to take care of this and move any significant work
   to a background thread or process. Executors also don't implement any kind
   of timeout mechanism. It's the :meth:`run` methods responsibility to make
   sure it always emits a `finished` signal.

.. note::
   Executors use :class:`~PyQt5.QtCore.QObject`s parent child properties to
   manage children.

"""

import abc
import logging
from enum import Enum, auto
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from RAMSIS.utils import QtABCMeta


class ExecutionStatus:
    """ 
    Status change notification for :cvar:`~_Executor.status_changed` signals

    :param AbstractExecutor or Executor origin: Original sender of the message
    :param ExecutionStatus.Flag flag: Status flag indicating the new status
    :param info: Additional Executor specific info

    """

    class Flag(Enum):
        STARTED = auto()  #: Execution has started successfully
        RUNNING = auto()   #: Execution is currently processing
        SUCCESS = auto()  #: Execution has finished successfully
        ERROR = auto()    #: Execution has finished with an error

    def __init__(self, origin, flag=Flag.SUCCESS, info=None):
        self.origin = origin
        self.flag = flag
        self.info = info


class AbstractExecutor(QObject, metaclass=QtABCMeta):
    """ Executor base class """

    #: pyqtSignal emitted when the execution status has changed. Child
    #    execution status changes will be forwarded via this too.
    status_changed = pyqtSignal(object)

    def __init__(self, **kwargs):
        """
        :param kwargs: These are passed on to QObject
        """
        super().__init__(**kwargs)

    def pre_process(self):
        """
        Execution pre-processing

        Invoked before any children are executed
        """
        pass

    def post_process(self):
        """
        Execution post-processing

        Invoked after all children have finished executing but before the
        `finished` signal is emitted
        """
        pass

    @abc.abstractmethod
    def run(self):
        pass

    def on_child_status_changed(self, execution_status):
        """
        Forwards the status change notification up the executor chain

        .. note: Note that *any* :cvar:`status_changed` signal is forwarded up
                 the executor chain all the way to the top. This allows clients
                 to act on any status change anywhere in the execution chain.

        """
        self.status_changed.emit(execution_status)


class SerialExecutor(AbstractExecutor):
    """
    Executes its children sequentially.

    Invoking :meth:`run` starts the first child. After the first child signals
    that it has completed execution, the next child is started, and so on.
    When the last child completes, the `SerialExecutor`
    runs :meth:`post_process` and then emits its own `status_changed` signal
    with a status of :cvar:`~ExecutionStatus.Status.SUCCESS`. If any child
    reports an error, the executor stops and emits an
    :cvar:`~ExecutionStatus.Status.ERROR` status itself unless
    :cvar:`~ExecutionStatus.Status.ERROR` is in the :ivar:`proceed_on` list in
    which case execution continues until all children have completed.
    If not children are present, `SUCCESS` is emitted immediately upon run.

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.proceed_on = [ExecutionStatus.Flag.SUCCESS]
        self._iter = None

    def run(self):
        self.status_changed.emit(ExecutionStatus(self,
                                                 ExecutionStatus.Flag.STARTED))
        self._iter = iter(self.children())
        self.pre_process()
        self._run_next()

    def on_child_status_changed(self, execution_status):
        super().on_child_status_changed(execution_status)
        if execution_status.origin in self.children() and \
                (execution_status.flag in self.proceed_on):
            self._run_next()

    def _run_next(self):
        try:
            executor = next(self._iter)
            executor.status_changed.connect(self.on_child_status_changed,
                                            Qt.UniqueConnection)
        except StopIteration:
            self._iter = None
            self.post_process()
            self.status_changed.emit(ExecutionStatus(self))
        else:
            executor.run()


class ParallelExecutor(AbstractExecutor):
    """
    Executes child executors in parallel

    All child executors are started immediately. A `status_changed` signal
    with a status of :cvar:`~ExecutionStatus.Status.SUCCESS` is emitted as soon
    as all children have reported completion. It is also emitted (immediately)
    if no children are present.

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._completed = {}

    def run(self):
        self.status_changed.emit(ExecutionStatus(self,
                                                 ExecutionStatus.Flag.STARTED))
        self._completed = {}
        self.pre_process()
        if not self.children():
            self._wrap_up()
        else:
            for executor in self.children():
                executor.status_changed.connect(self.on_child_status_changed,
                                                Qt.UniqueConnection)
                executor.run()

    def on_child_status_changed(self, status):
        super().on_child_status_changed(status)
        if status.origin in self.children():
            self._completed[status.origin] = status
        if len(self._completed) == len(self.children()):
            self._wrap_up()

    def _wrap_up(self):
        self.post_process()
        self.status_changed.emit(ExecutionStatus(self))


class Executor(QObject, metaclass=QtABCMeta):
    """
    A simple executor with no children

    A simple executor implements it's work in the run method. The run method
    is expected to return immediately, i.e. any significant work should be
    offloaded to a separate thread or process. Also, make sure to  *always*
    emit the `status_changed` signal, even when the operation times out.

    """

    #: pyqtSignal emitted when execution has finished
    status_changed = pyqtSignal(object)

    def __init__(self, **kwargs):
        """
        :param kwargs: These are passed on to QObject
        """
        super().__init__(**kwargs)

    @abc.abstractmethod
    def run(self):
        pass
