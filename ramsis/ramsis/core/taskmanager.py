# -*- encoding: utf-8 -*-
"""
Manages scheduled tasks in ramsis


Copyright (C) 2017, ETH Zurich - Swiss Seismological Service SED

"""

import logging
from datetime import timedelta
from tools.scheduler import Task, TaskScheduler, PeriodicTask


class TaskManager:
    """
    Manages the ramsis specific scheduler and tasks

    """

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
                'dt_setting': 'rate_interval',
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

        self.core.project_loaded.connect(self.on_project_loaded)

    def reset(self, t0=None):
        self.scheduler.reset(t0 or self.core.project.start_date)

    # Signal handlers

    def on_project_loaded(self, project):
        for task in self.scheduler.scheduled_tasks:
            if task.name in self.periodic_tasks:
                task.t0 = project.start_date
                dt_setting = self.periodic_tasks[task.name]['dt_setting']
                task.dt = timedelta(minutes=project.settings[dt_setting])
        self.scheduler.reset(project.project_time)
        project.project_time_changed.connect(self.on_project_time_change)

    def on_project_time_change(self, t_project):
        if self.scheduler.has_due_tasks(t_project):
            self.logger.debug('Scheduler has pending tasks. Executing')
            self.logger.debug('Run pending tasks')
            self.scheduler.run_due_tasks(t_project)

    # Task Methods

    def fetch_fdsn(self, t):
        """ FDSN task function """
        p = self.core.project
        if p:
            dt = p.settings.value('fdsnws_interval')
            end = p.project_time
            # FIXME: we should have an overlap in our data fetches to catch
            # updated events
            start = p.project_time - dt
            self.core.seismics_data_source.fetch(starttime=start, endtime=end)

    def fetch_hydws(self, t):
        """ HYDWS task function """
        p = self.core.project
        if p:
            dt = p.settings.value('hydws_interval')
            end = p.project_time
            # FIXME: we should have an overlap in our data fetches to catch
            # updated events
            start = p.project_time - dt
            self.core.hydraulics_data_source.fetch(starttime=start,
                                                   endtime=end)

    def update_rates(self, t):
        """ Rate computation task function """
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
        self.core.engine.run(t, self.forecast_task.next_forecast)
        # prepare the next regular forecast
        self._add_next_forecast()

    def _add_next_forecast(self):
        p = self.core.project
        dt = timedelta(hours=p.settings['forecast_interval'])
        if self.forecast_task.next_forecast:
            t_next = self.forecast_task.next_forecast.forecast_time + dt
        else:
            t_next = p.start_date + dt
        next_forecast = p.forecast_set.forecast_at(t_next)
        if next_forecast is None:
            next_forecast = self.core.create_forecast(t_next)
            p.forecast_set.add_forecast(next_forecast)
            p.commit()


class ForecastTask(Task):
    """
    Schedules and runs the next forecast

    """

    def __init__(self, task_function, core):
        super(ForecastTask, self).__init__(task_function, name='ForecastTask')
        self.next_forecast = None
        self.run_time = None
        self.core = core

    def schedule(self, t):
        """
        Schedule the next forecast

        This method simply looks for the next forecast that hasn't been
        completed yet and whose forecast_time is after t.

        """

        if self.core.project is None:
            return

        forecasts = self.core.project.forecast_set.forecasts
        try:
            self.next_forecast = next(f for f in forecasts if not f.complete
                                      and f.forecast_time > t)
            self.run_time = self.next_forecast.forecast_time
        except StopIteration:
            self.next_forecast = None
            self.run_time = None
