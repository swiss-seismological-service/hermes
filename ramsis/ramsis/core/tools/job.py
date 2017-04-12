# -*- coding: utf-8 -*-
"""
Base classes for parallel or serial execution of work work_units

Jobs can be nested or, i.e. a job can act as a work_unit for another job.

Copyright (c) 2017, Swiss Seismological Service, ETH Zurich

"""

from PyQt4.QtCore import QObject, pyqtSignal


class Job(QObject):
    """
    Abstract base class for a job

    :ivar dict shared_data: Shared data between work units and the job. The
        attribute is typically used to share input and output data, however
        it is completely up to the work units what to do with it.
    :ivar [WorkUnit] work_units: list of work units for this job

    :param str job_id: an id for this job


    """

    complete = pyqtSignal(object)

    def __init__(self, job_id):
        super(Job, self).__init__()
        self.job_id = job_id
        self._work_units = []

    @property
    def work_units(self):
        return self._work_units

    @work_units.setter
    def work_units(self, work_units):
        self._work_units = work_units
        for unit in work_units:
            unit.complete.connect(self._on_complete)

    def pre_process(self):
        pass

    def post_process(self):
        pass

    def _on_complete(self, unit):
        pass


class SerialJob(Job):
    """
    A job that executes its work units in sequence

    The next unit is only started when the previous unit has
    sent its *complete* signal. The jobs complete signal is
    emitted after the last unit has completed.

    """

    def __init__(self, job_id):
        super(SerialJob, self).__init__(job_id)
        self._iter = None

    def run(self):
        self._iter = iter(self.work_units)
        self.pre_process()
        self._run_next()

    def _on_complete(self, unit):
        self._run_next()

    def _run_next(self):
        try:
            work_unit = next(self._iter)
        except StopIteration:
            self._iter = None
            self.post_process()
            self.complete.emit(self)
        else:
            work_unit.run()


class ParallelJob(Job):
    """
    A job that executes its work units in parallel

    All work units are started concurrently. The job's *complete*
    signal is emitted when all work units have sent their *complete*
    signal.

    """

    def __init__(self, job_id):
        super(ParallelJob, self).__init__(job_id)
        self._completed_units = []

    def run(self):
        self._completed_units = []
        self.pre_process()
        for unit in self.work_units:
            unit.run()

    def _on_complete(self, unit):
        self._completed_units.append(unit)
        if len(self.work_units) == len(self._completed_units):
            self.post_process()
            self.complete.emit(self)


class WorkUnit(QObject):
    """
    A unit of work within a job

    Override run in the subclass and make sure to emit the *complete* signal at
    the end of *run* and pass self

    """

    complete = pyqtSignal(object)

    def __init__(self, work_unit_id):
        super(WorkUnit, self).__init__()
        self.work_unit_id = work_unit_id

    def run(self):
        pass
