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
    care of managing those stages.

    Derived classes should at a minimum set the job_id (str) and the stages
    attribute. The latter is a list of `Stage` derived classes that the `Job`
    instantiates and executes sequentially.

    Each stage has access to the job and thus to the shared 'data' attribute.
    The data attribute is a dict containing 'input' and results for each
    stage under the respective stage_id key

    :ivar str job_id: Unique identifier for the job
    :ivar list[Stage] stages: List of stage objects
    :ivar dict data: input and output data for the job and each stage

    """

    job_complete = QtCore.pyqtSignal(object)

    def __init__(self, job_id, stages):
        super(Job, self).__init__()
        self.job_id = job_id
        self.stages = stages
        self._runnable_stages = None
        self._logger = logging.getLogger(__name__)
        self.data = {}
        for stage in stages:
            stage.job = self
            stage.callback = self._stage_complete

    def run(self, job_input):
        """
        Runs the job.

        """
        self.data['input'] = job_input
        self._runnable_stages = self._stage_gen()
        next(self._runnable_stages).run()

    def _job_complete(self):
        self.job_complete.emit(self)

    def _stage_complete(self, completed_stage):
        self.data[completed_stage.stage_id] = completed_stage.results
        try:
            next(self._runnable_stages).run()
        except StopIteration:
            self._logger.info('{} job complete'.format(self.job_id))
            self._job_complete()

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

    stage_complete = QtCore.pyqtSignal(object)

    def __init__(self, stage_id):
        self.stage_id = stage_id
        self.job = None
        self.completed = False
        self.results = None
        self._logger = logging.getLogger(__name__)

    def run(self):
        """
        Runs the stage by setting the inputs and executing `stage_fun`.

        :param inputs: Stage input data

        """
        self.stage_fun()
        self.completed = True
        self.stage_complete.emit(self)

    def stage_fun(self):
        """
        Executes the stage. The default implementation does nothing.
        Subclasses should implement this function and set ``self.results`` on
        completion.

        """
        pass


