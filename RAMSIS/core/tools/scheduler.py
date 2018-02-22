# -*- encoding: utf-8 -*-
# Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED
"""
The classes in this module implement a simple task scheduler that executes
tasks at certain points in time or at regular intervals. Tasks should not run
for long periods of time since they are executed on the main thread.

"""

import logging
from datetime import timedelta

class Task(object):
    """
    Scheduled Task

    The task will be executed at run_time by calling task_function and passing
    it the current time t. Name is purely informational (for logging). One off
    tasks will be removed from the scheduler after execution.

    """

    def __init__(self, task_function, name='Task'):
        self.name = name
        self.task_function = task_function
        self.run_time = None
        self.one_off = True

    def is_due(self, t):
        return t >= self.run_time if self.run_time is not None else False

    def run(self, t):
        self.task_function(t)
        self.run_time = None

    def schedule(self, t):
        """
        Schedule next execution

        This method will not be called on one-off tasks.

        """
        pass


class PeriodicTask(Task):
    """
    A  periodic task.

    The task manages its own scheduling interval and time for next execution.

    """

    def __init__(self, task_function, name='PeriodicTask'):
        super(PeriodicTask, self).__init__(task_function, name)
        self.t0 = None
        self.dt = None
        self.run_time = None
        self.task_function = task_function
        self.one_off = False

    def run(self, t):
        """
        Runs the task by invoking the run_function and passing the time at
        which the task is run.

        """
        self.task_function(t)

    def schedule(self, t):
        r = int((t - self.t0).total_seconds()) % int(self.dt.total_seconds())
        self.run_time = t - timedelta(seconds=r) + self.dt


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

    def reset(self, t):
        """
        Reset the scheduled times by scheduling the first runs for all
        repeating tasks based on `t0`. One-off tasks are removed.

        """
        self.scheduled_tasks = [task for task in self.scheduled_tasks
                                if not task.one_off]
        for task in self.scheduled_tasks:
            task.schedule(t)

    def due_tasks(self, t):
        return [task for task in self.scheduled_tasks if task.is_due(t)]

    def has_due_tasks(self, t):
        return True if len(self.due_tasks(t)) > 0 else False

    def run_due_tasks(self, t):
        """
        Run all tasks that are due at time t. After running, tasks are
        scheduled for the next execution and one-off tasks are
        removed from the task queue.

        :param datetime.datetime t: current time

        """
        for task in self.scheduled_tasks:
            if task.is_due(t):
                self._logger.debug('Running Task: ' + task.name)
                task.run(t)
                if task.one_off:
                    self.scheduled_tasks.remove(task)
                else:
                    task.schedule(t)

