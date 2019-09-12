# -*- encoding: utf-8 -*-
"""
Manages scheduled tasks in ramsis


Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED

"""

import logging
from datetime import timedelta
from .tools.scheduler import Task, TaskScheduler, PeriodicTask


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
        self.forecast_task = ForecastTask(task_function=self.run_forecast,
                                          core=self.core)
        self.scheduler.add_task(self.forecast_task)

        self.periodic_tasks = {
            'Rate update': {
                'dt_setting': 'seismic_rate_interval',
                'function': self.update_rates
            },
            'FDSNWS': {
                'dt_setting': 'fdsnws_interval',
                'function': self.fetch_fdsn
            },
            'HYDWS': {
                'dt_setting': 'hydws_interval',
                'function': self.fetch_hydws
            },
        }

        for name, info in self.periodic_tasks.items():
            task = PeriodicTask(task_function=info['function'],
                                name=name)
            self.scheduler.add_task(task)
        self.core.clock.time_changed.connect(self.on_time_changed)
        self.core.project_loaded.connect(self.on_project_loaded)

    def reset(self, t0=None):
        self.scheduler.reset(t0 or self.core.project.start_date)

    # Signal handlers

    def on_project_loaded(self, project):
        for task in self.scheduler.scheduled_tasks:
            if task.name in self.periodic_tasks:
                task.t0 = project.starttime
                dt_setting = self.periodic_tasks[task.name]['dt_setting']
                task.dt = timedelta(minutes=project.settings[dt_setting])
        self.scheduler.reset(project.starttime)

    def on_time_changed(self, time):
        if self.scheduler.has_due_tasks(time):
            self.logger.debug('Scheduler has due tasks. Executing.')
            self.scheduler.run_due_tasks(time)

    # Task Methods

    def fetch_fdsn(self, t):
        """ FDSN task function """
        if None in (self.core.project, self.core.seismics_data_source):
            return

        p = self.core.project
        try:
            dt = p.settings['fdsnws_interval']
        except KeyError as err:
            self.logger.warning(
                f'Invalid project configuration: {err}')
        else:
            start = p.starttime
            if len(p.seismiccatalog):
                start = (t - timedelta(minutes=dt) -
                         self.THRESHOLD_DATASOURCES)
            self.core.seismics_data_source.fetch(
                starttime=start, endtime=t)

    def fetch_hydws(self, t):
        """ HYDWS task function """
        if None in (self.core.project, self.core.hydraulics_data_source):
            return

        p = self.core.project
        try:
            dt = p.settings['hydws_interval']
        except KeyError as err:
            self.logger.warning(
                f'Invalid project configuration: {err}')
        else:
            start = p.starttime
            if (p.wells and p.wells[0].sections and
                    len(p.wells[0].sections[0].hydraulics)):
                start = (t - timedelta(minutes=dt) -
                         self.THRESHOLD_DATASOURCES)
            self.core.hydraulics_data_source.fetch(
                starttime=start, endtime=t)

    def update_rates(self, t):
        """ Rate computation task function """
        # TODO LH: reimplement. We don't have a rate history on the project any
        #   more. However, this should be cheap to compute, so we can probably
        #   just implement a RateComputer that recomputes all rates on the fly
        #   (and allows filtering on magnitude bins).
        # t_run = info.t_project
        # seismic_events = self.project.seismic_catalog.events_before(t_run)
        # data = [(e.date_time, e.magnitude) for e in seismic_events]
        # if len(data) == 0:
        #     return
        # t, m = zip(*data)
        # t = list(t)
        # m = list(m)
        # rates = self.project.rate_history.compute_and_add(m, t, [t_run])
        # self._logger.debug('New rate computed: ' + str(rates[0].rate))
        pass

    def run_forecast(self, t):
        self.logger.info('Forecast initiated at {}'.format(t))
        self.core.engine.run(t, self.forecast_task.next_forecast)


class ForecastTask(Task):
    """
    Schedules and runs the next forecast

    """

    def __init__(self, task_function, core):
        super(ForecastTask, self).__init__(task_function, name='ForecastTask')
        self.next_forecast = None
        self.run_time = None
        self.one_off = False
        self.core = core

    def schedule(self, t):
        """
        Schedule the next regular forecast

        This method simply looks for the next forecast that hasn't been
        completed yet and whose forecast_time is after t.

        """

        if self.core.project is None:
            return

        forecasts = self.core.project.forecasts
        try:
            self.next_forecast = next(f for f in forecasts if f.starttime > t)
            self.run_time = self.next_forecast.starttime
        except StopIteration:
            self.next_forecast = None
            self.run_time = None
