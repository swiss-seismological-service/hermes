# -*- encoding: utf-8 -*-
"""
Runs oq in a separate process

This file will be imported by the child process

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""
import os
import time
import getpass

# OpenQuake modules
import openquake.engine
import openquake.engine.engine as oe
from openquake.engine.utils import config
from openquake.engine.db.schema.upgrades import upgrader
from openquake.engine.celery_node_monitor import CeleryNodeMonitor
from django import db as django_db

config.abort_if_no_config_available()


# no distribute for now
OQ_DISTRIBUTE = False

# Initial configuration and checks
# set if we run distributed or not
os.environ[openquake.engine.NO_DISTRIBUTE_VAR] = '0' if OQ_DISTRIBUTE else '1'
# first of all check the database version and exit if the db is outdated
upgrader.check_versions(django_db.connections['admin'])


def run_job(queue, job_input):
    """
    Run a job using the specified job definition file and other options.

    This function executes in a separate process

    :param queue: queue to report results back to the main process
    :type queue: multiprocessing.Queue

    """

    # Job input defaults
    inputs = {
        'hazard_calculation_id': None,
        'hazard_output_id': None,
        'oq_log_file': None,
        'oq_exports': (),
        'oq_log_level': 'progress'
    }
    inputs.update(job_input)
    assert 'job_def' in inputs, 'job_def is a required input'

    result = {'success': False}
    with CeleryNodeMonitor(openquake.engine.no_distribute(), interval=3):
        hazard = (inputs['hazard_output_id'] is None and
                  inputs['hazard_calculation_id'] is None)
        if inputs['oq_log_file'] is not None:
            touch_log_file(inputs['log_file'])

        job = oe.job_from_file(inputs['job_def'], getpass.getuser(),
                               inputs['oq_log_level'], inputs['oq_exports'],
                               inputs['hazard_output_id'],
                               inputs['hazard_calculation_id'])

        # Instantiate the calculator and run the calculation.
        t0 = time.time()
        queue.put('Running job #{}.'.format(job.id))
        oe.run_calc(job, inputs['oq_log_level'], inputs['oq_log_file'],
                    inputs['oq_exports'])
        duration = time.time() - t0
        if hazard:
            job_type = 'hazard'
        else:
            job_type = 'risk'

        if job.status == 'complete':
            queue.put('OQ {} calculation #{} completed in {}s.'
                      .format(job_type, job.id, duration))
            result['success'] = True
        else:
            queue.put('OQ {} calculation #{} failed.'.format(job_type, job.id))
            result['success'] = False
        result['job_id'] = job.id
        queue.put(result)


# replicated from oq engine.py
def touch_log_file(log_file):
    """
    If a log file destination is specified, attempt to open the file in
    'append' mode ('a'). If the specified file is not writable, an
    :exc:`IOError` will be raised.
    """
    open(os.path.abspath(log_file), 'a').close()
