# -*- encoding: utf-8 -*-
"""
ATLS Job management

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from PyQt4 import QtCore
import logging


class Job(QtCore.QObject):
    """
    A job is the most high level computational unit in ATLS

    A job consists of stages that are run in succession. The Job class takes
    care of managing those stages, passing intermediate results to the next
    stage and reporting final results back to the framework.

    Derived classes should set the job_id (str) and stages attributes. The
    latter is a list of Stage classes.

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

    Derived classes should set the stage_id (str) and implement the stage_fun
    function that does the actual work of the stage.

    """
    stage_id = None

    def __init__(self, callback):
        """
        Derived classes should set stage_id on init.

        :param callback: callback invoked when stage completes
        :type callback: method taking one argument (the stage)

        """
        assert self.stage_id is not None, "You must set a stage id"
        self.inputs = None
        self.completed = False
        self.results = None
        self.callback = callback
        self._logger = logging.getLogger(__name__)

    def run(self, inputs):
        self.inputs = inputs
        self.stage_fun()

    def stage_fun(self):
        """
        Executes the stage. The default implementation completes immediately.
        Subclasses should implement this function set self.results on
        completion and call stage_complete at the end.

        The when this method is invoked, the inputs to the stage are available
        in self.inputs.

        """
        pass

    def stage_complete(self):
        self.completed = True
        self.callback(self)
