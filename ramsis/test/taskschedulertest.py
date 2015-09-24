# -*- encoding: utf-8 -*-
"""
Unit test for the taskscheduler module

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from datetime import timedelta, datetime

from mock import MagicMock

from scheduler.taskscheduler import TaskScheduler, ScheduledTask


class ScheduledTaskTest(unittest.TestCase):
    """ Tests the ScheduledTask class """

    def handler(self, info):
        pass

    def test_create_task(self):
        """
        Tasks can be created with or without a repeat interval and with
        or without a name (in which case we expect a default name).

        """
        def dummy():
            pass

        dt = timedelta(minutes=10)
        task = ScheduledTask(self.handler, dt=dt, name='MyTask')
        self.assertEqual(task.dt, dt)
        self.assertEqual(task.name, 'MyTask')

        task = ScheduledTask(self.handler)
        self.assertIsNone(task.dt)
        self.assertIsNotNone(task.name)

    def test_schedule(self):
        """ Test task scheduling """
        t_run = datetime(2011, 10, 14, 17, 23)
        dt = timedelta(hours=1)

        single = ScheduledTask(self.handler)
        repeating = ScheduledTask(self.handler, dt=dt)

        # This should raise an error since the repeating task has not been
        # scheduled with an absolute time before
        with self.assertRaises(TypeError):
            repeating.schedule()

        # This should schedule the task to execute at t_run
        single.schedule(t_run=t_run)
        repeating.schedule(t_run=t_run)
        self.assertEqual(single.run_time, t_run)
        self.assertEqual(repeating.run_time, t_run)

        # This should schedule the repeating task at t_run + dt
        repeating.schedule()
        self.assertEqual(repeating.run_time, t_run + dt)

        # This should raise an error
        with self.assertRaises(TypeError):
            single.schedule()

    def test_pending(self):
        """ Test if a task correctly infers if it is pending or not """
        t_run = datetime(2011, 10, 14, 17, 23)
        dt = timedelta(seconds=1)

        task = ScheduledTask(self.handler)
        task.schedule(t_run)

        self.assertTrue(task.is_pending(t_run))
        self.assertTrue(task.is_pending(t_run + dt))
        self.assertFalse(task.is_pending(t_run - dt))

    def test_run(self):
        handler = MagicMock()
        info = MagicMock()
        task = ScheduledTask(handler)
        task.run(info)

        handler.assert_called_once_with(info)


class TaskSchedulerTest(unittest.TestCase):
    """ Tests the TaskScheduler class """

    def setUp(self):
        """ Setup a combination of differently scheduled tasks """
        self.scheduler = TaskScheduler()
        self.handler = MagicMock()
        self.t_run = datetime(2011, 10, 14, 17, 23)
        dt = timedelta(minutes=1)

        # repeating, at t_run
        self.task1 = ScheduledTask(self.handler, dt)
        self.task1.schedule(self.t_run)
        self.scheduler.add_task(self.task1)

        # single, at t_run
        self.task2 = ScheduledTask(self.handler)
        self.task2.schedule(self.t_run)
        self.scheduler.add_task(self.task2)

        # single, unscheduled
        self.task3 = ScheduledTask(self.handler)
        self.scheduler.add_task(self.task3)

        # single, at t_run + 1min
        self.task4 = ScheduledTask(self.handler)
        self.task4.schedule(self.t_run + dt)
        self.scheduler.add_task(self.task4)

        # repeating, at t_run + 1min
        self.task5 = ScheduledTask(self.handler, dt)
        self.task5.schedule(self.t_run + dt)
        self.scheduler.add_task(self.task5)

    def test_pending(self):
        """ Test inquiries about pending tasks """
        dt = timedelta(seconds=1)
        self.assertTrue(self.scheduler.has_pending_tasks(self.t_run))
        self.assertFalse(self.scheduler.has_pending_tasks(self.t_run - dt))
        self.assertListEqual(self.scheduler.pending_tasks(self.t_run),
                             [self.task1, self.task2])

    def test_reset_schedule(self):
        """
        Reset schedule should reschedule repeating tasks and remove simple
        tasks

        """
        self.scheduler.reset_schedule(self.t_run)

        self.assertListEqual(self.scheduler.scheduled_tasks,
                             [self.task1, self.task5])
        self.assertEqual(self.task1.run_time, self.t_run + self.task1.dt)
        self.assertEqual(self.task5.run_time, self.t_run + self.task5.dt)

    def test_run_pending(self):
        """ Test running pending tasks and updating schedule """
        self.scheduler.run_pending_tasks(self.t_run, None)
        self.assertEqual(self.handler.call_count, 2)
        self.assertEqual(self.task1.run_time, self.t_run + self.task1.dt)
        self.assertEqual(self.task5.run_time, self.t_run + self.task5.dt)


if __name__ == '__main__':
    unittest.main()
