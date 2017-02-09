# -*- encoding: utf-8 -*-
# Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED
"""
The classes in this module implement a simple task scheduler that executes
code at certain points in time or at regular intervals.

"""

import logging


class ScheduledTask:
    """
    A scheduled task.

    The task manages its own scheduling interval and time for next execution.

    Create a new task by providing a function to run at the
    scheduled time and an optional scheduling interval for repeating tasks.
    The name is optional too and is simply used for logging purposes.

    :param task_function: the function which TaskScheduler invokes when the
        task should run. This function must take one argument which is the
        run_info object that contains everything the task needs in order
        to execute.
    :param dt: optional scheduling interval for repeating tasks
    :type dt: timedelta
    :param name: name of the task
    :type name: str

    """

    def __init__(self, task_function, dt=None, name='Task'):
        self.name = name
        self.dt = dt
        self.run_time = None
        self.task_function = task_function

    def is_pending(self, t):
        """
        Return True if execution is pending at time *t*

        :param datetime.datetime t: time to check against scheduled execution
            time

        """
        return t >= self.run_time if self.run_time is not None else False

    def schedule(self, t_run=None):
        """
        Schedule the next execution at t_run.

        For a repeating task, t_run does not have to be provided (except on the
        first call). In that case the tasks next execution will be scheduled on
        the previous execution time + dt.

        :param datetime.datetime t_run: time at which to run the task

        """
        if t_run is None:
            self.run_time += self.dt
        else:
            self.run_time = t_run

    def run(self, run_info):
        """
        Runs the task by invoking the run_function and passing the run_info
        dictionary to it.

        """
        self.task_function(run_info)


class TaskScheduler:
    """
    Manages and executes scheduled tasks.

    You add tasks to the list using `add_task`.

    """

    def __init__(self):
        """
        Initialize a scheduler with a list of tasks

        """
        # Maintain a list of scheduled tasks
        self.scheduled_tasks = []
        self._logger = logging.getLogger(__name__)

    def add_task(self, task):
        """
        Add a new task to the scheduler

        :param ScheduledTask task: Task to add

        """
        self.scheduled_tasks.append(task)

    def reset_schedule(self, t0):
        """
        Reset the scheduled times by scheduling the first runs for all
        repeating tasks based on `t0`. Non-repeating tasks are removed.

        """
        self.scheduled_tasks = [task for task in self.scheduled_tasks
                                if task.dt is not None]
        for task in self.scheduled_tasks:
            task.run_time = t0 + task.dt

    def pending_tasks(self, t):
        return [task for task in self.scheduled_tasks if task.is_pending(t)]

    def has_pending_tasks(self, t):
        return True if len(self.pending_tasks(t)) > 0 else False

    def run_pending_tasks(self, t, run_info):
        """
        Run all tasks that are pending at time t. After running, repeating
        tasks are scheduled for the next execution and non-repeating tasks are
        removed from the task queue.

        :param datetime.datetime t: time t against which the schedule is
            checked
        :param run_info: object that will be passed to the task function

        """
        for task in self.scheduled_tasks:
            if task.is_pending(t):
                self._logger.debug('Running Task: ' + task.name)
                task.run(run_info)

        self._update_schedule(t)

    def _update_schedule(self, t):
        """
        Schedule next task execution.

        The function checks which tasks need rescheduling at time t and
        schedules their next execution.

        """
        for task in self.scheduled_tasks:
            if task.is_pending(t):
                if task.dt is None:
                    self.scheduled_tasks.remove(task)
                else:
                    task.schedule()
