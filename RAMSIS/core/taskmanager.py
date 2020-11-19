# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Manages scheduled tasks in ramsis
"""

from time import sleep
import logging
import operator
from datetime import timedelta, datetime
from PyQt5.QtCore import QThread
from .tools.scheduler import Task, TaskScheduler
from ramsis.datamodel.status import EStatus

datetime_format = '%Y-%m-%dT%H:%M:%S.%f'


class TaskManager:
    """
    Manages the ramsis specific scheduler and tasks

    """
    THRESHOLD_DATASOURCES = timedelta(seconds=60)

    def __init__(self, core):
        self.core = core
        self.scheduler = TaskScheduler()
        self.logger = logging.getLogger(__name__)

        # Add forecast Task
        self.forecast_task = ForecastTask(task_function=self.run_forecasts,
                                          core=self.core)
        print("added forecast_task")
        self.scheduler.add_task(self.forecast_task)
        self.core.clock.time_changed.connect(self.on_time_changed)
        self.core.project_loaded.connect(self.on_project_loaded)

    def reset(self, t0=None):
        self.scheduler.reset(t0 or self.core.project.starttime)

    # Signal handlers

    def on_project_loaded(self, project):
        # Why should we always reset based on the project starttime?
        # self.scheduler.reset(project.starttime)
        pass

    def on_time_changed(self, time):
        if self.scheduler.has_due_tasks(time):
            self.logger.debug('Scheduler has due tasks. Executing.')
            self.scheduler.run_due_tasks(time)
        self.forecast_task.update_forecasts(time)

    def run_forecasts(self, t):
        self.forecasts_runner = RunForecasts(
            self.core, self.forecast_task.forecasts_to_run(t), t)
        self.forecasts_runner.start()


class RunForecasts(QThread):
    """
    Add seperate thread for waiting to run forecast based
    on data collection.
    """
    def __init__(self, core, forecasts, t):
        super().__init__()
        self.core = core
        self.logger = logging.getLogger(__name__)
        self.forecasts = forecasts
        self.time_scheduled = t

        self.logger.info(f'Forecasts due {forecasts} initiated at {t}')

    def run(self):
        self.fetch_fdsn(self.time_scheduled)
        self.fetch_hydws(self.time_scheduled)
        self.logger.info(f'Forecasts due {self.forecasts} start run at '
                         f'{datetime.utcnow()}')
        sleep(3)
        for ind, forecast in enumerate(self.forecasts):
            self.logger.info('forecasts #{}'.format(ind))
            self.core.engine.run(self.time_scheduled, forecast.id)

    def fetch_fdsn(self, t, last_run=None):
        """
        FDSN task function

        :param t: Current execution time
        :type t: :py:class:`datetime.datetime`
        :param last_run: Execution time of the previous execution
        :type last_run: :py:class:`datetime.datetime`
        """
        self.logger.info("Fetch fdsn called")
        if None in (self.core.project, self.core.seismics_data_source):
            self.logger.info("No FSDN URL configured")
            return

        p = self.core.project
        try:
            dt = p.settings['fdsnws_interval']
        except KeyError as err:
            self.logger.warning(
                f'Invalid project configuration: {err}')
        else:
            start = p.starttime
            if p.seismiccatalog and len(p.seismiccatalog) and last_run:
                start = (last_run - timedelta(minutes=dt) -
                         self.THRESHOLD_DATASOURCES)
            self.core.seismics_data_source.fetch(
                starttime=datetime.strftime(
                    start, datetime_format),
                endtime=datetime.strftime(t, datetime_format))
            self.core.seismics_data_source.wait()

    def fetch_hydws(self, t, last_run=None):
        """
        HYDWS task function

        :param t: Current execution time
        :type t: :py:class:`datetime.datetime`
        :param last_run: Execution time of the previous execution
        :type last_run: :py:class:`datetime.datetime`
        """
        self.logger.info("Fetch hydws called")
        if None in (self.core.project, self.core.hydraulics_data_source):
            self.logger.info("No HYDWS URL configured")
            return

        p = self.core.project
        try:
            dt = p.settings['hydws_interval']
        except KeyError as err:
            self.logger.warning(
                f'Invalid project configuration: {err}')
        else:
            start = p.starttime
            if (p.well and p.well.sections and
                p.well.sections[0].hydraulics and
                    last_run):
                start = (last_run - timedelta(minutes=dt) -
                         self.THRESHOLD_DATASOURCES)
            self.core.hydraulics_data_source.fetch(
                starttime=datetime.strftime(start, datetime_format),
                endtime=datetime.strftime(t, datetime_format),
                level='hydraulic')
            self.core.hydraulics_data_source.wait()


class ForecastTask(Task):
    """
    Schedules and runs the next forecast

    """

    def __init__(self, task_function, core):
        super(ForecastTask, self).__init__(task_function, name='ForecastTask')
        self.forecasts = []
        self.core = core

    def schedule(self, t):
        """
        Schedule the next regular forecast

        This method simply looks for the next forecast that hasn't been
        completed yet and whose forecast_time is after t.

        """
        if self.core.project is None:
            return
        self.update_forecasts(t)

    def update_forecasts(self, t):
        try:
            # Update self.forecasts to be up to date with which
            # forecasts are still pending.
            self.forecasts = sorted([
                f for f in self.core.project.forecasts if
                f.status.state == EStatus.PENDING],
                key=operator.attrgetter('starttime'))
            # Find the next run time for a forecast.
            if self.forecasts:
                self.run_time = min([f.starttime for f in self.forecasts])
        except (StopIteration, ValueError):
            self.forecasts = []
            self.run_time = None

    def forecasts_to_run(self, t):
        return [f for f in self.forecasts if f.starttime < t]
