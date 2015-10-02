# -*- encoding: utf-8 -*-
# Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED
"""
RAMSIS Job management

"""

from PyQt4 import QtCore
import logging


class Job(QtCore.QObject):
    """
    Multi stage computational unit.

    A job consists of stages that are run in succession. The Job class takes
    care of managing those stages, passing intermediate results to the next
    stage and reporting final results back to the framework.

    Derived classes should at a minimum set the job_id (str) and the stages
    attributes. The latter is a list of `Stage` derived classes that `Job`.

    :ivar str job_id: Unique identifier for the job
    :ivar list[Stage] stages: List of classes that represent the `Jobs <Job>`
        different stages.

    """

    stage_completed = QtCore.pyqtSignal(object)
    job_id = None
    stages = None

    def __init__(self):
        assert self.job_id is not None, "You must set a job id"
        assert self.stages is not None, "You must set a list of stages"
        super(Job, self).__init__()
        self.stage_objects = [S(self._stage_complete) for S in self.stages]
        self._runnable_stages = None
        self._logger = logging.getLogger(__name__)

    def run(self, inputs):
        """
        Runs the job.

        """
        self._runnable_stages = self._stage_gen()
        next(self._runnable_stages).run(inputs)

    def _stage_complete(self, completed_stage):
        self.stage_completed.emit(completed_stage)
        try:
            next(self._runnable_stages).run(completed_stage.results)
        except StopIteration:
            self._logger.info('{} job complete'.format(self.job_id))
            return

    def _stage_gen(self):
        for stage in self.stage_objects:
            yield stage


class Stage(object):
    """
    Abstract base class for job stages.

    Derived classes should override `stage_id` and implement `stage_fun`.
    The latter does the actual work of the stage.

    :param callback: Callback invoked when stage completes (must take exactly
        one argument which is the `Stage` that just completed.
    :ivar inputs: Stage inputs, set with `run`.
    :ivar results: Stage results, set by `stage_fun` after completion
    :ivar completed: Set to True when the stage has completed

    """
    stage_id = None  #: Unique identifier for stage

    def __init__(self, callback):
        assert self.stage_id is not None, "You must set a stage id"
        self.inputs = None
        self.completed = False
        self.results = None
        self.callback = callback
        self._logger = logging.getLogger(__name__)

    def run(self, inputs):
        """
        Runs the stage by setting the inputs and executing `stage_fun`.

        :param inputs: Stage input data

        """
        self.inputs = inputs
        self.stage_fun()

    def stage_fun(self):
        """
        Executes the stage. The default implementation does nothing.
        Subclasses should implement this function, set ``self.results`` on
        completion and call `stage_complete` at the end.

        The when this method is invoked, the inputs to the stage are available
        in ``self.inputs``.

        """
        pass

    def stage_complete(self):
        """
        Must be called by `stage_fun` on completion.

        """
        self.completed = True
        self.callback(self)
