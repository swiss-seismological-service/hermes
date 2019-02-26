#!/usr/bin/env python3
# This is <client.py>
# -----------------------------------------------------------------------------
#
# Copyright (c) Daniel Armbruster (SED, ETH), Lukas Heiniger (SED, ETH)
#
# REVISION AND CHANGES
# 2018/04/17        V0.1    Daniel Armbruster
# =============================================================================
"""
Tool to test and simplify the communication with *RT-RAMSIS* worker
implementations.
"""
# XXX(damb): The client application adds lots of dependencies to
# ramsis.worker (e.g. ramsis.datamodel, sqlalchemy). In order to keep the
# ramsis.worker package slim it is made part of the RAMSIS package.

import argparse
import contextlib
import datetime
import json
import logging
import os
import sys
import time
import traceback
import uuid

from urllib.parse import urlparse

import requests

from osgeo import gdal, ogr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from ramsis.datamodel.project import Project
from ramsis.datamodel.forecast import Forecast, ForecastInput, Scenario
from ramsis.datamodel.hydraulics import InjectionPlan, InjectionSample
from ramsis.utils import real_file_path
from ramsis.utils.app import CustomParser, AppError
from ramsis.utils.error import Error, ExitCode
from ramsis.utils.protocol import (SFMWorkerInputMessageSchema,
                                   StatusCode)
from RAMSIS import __version__
from RAMSIS.core.engine.worker import RemoteSeismicityWorkerHandle

# -----------------------------------------------------------------------------
TIMEOUT_POLLING = 60


class InvalidProjectId(Error):
    """Invalid project identifier ({})."""


# -----------------------------------------------------------------------------
@contextlib.contextmanager
def session_scope(Session):
    """
    Provide a transactional scope around a series of operations.
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# session_scope ()


def url_worker(url_str):
    """
    Validate a URL.
    """
    try:
        url = urlparse(url_str)

        if (url.path or url.params or url.query or url.fragment or
                url.scheme not in ('http', 'https')):
            raise ValueError('Invalid RT-RAMSIS worker URL.')

        return url.geturl()
    except Exception as err:
        raise argparse.ArgumentTypeError(err)

# url ()


def db_engine(url_str):
    """
    Validate a DB URL and return an engine.
    """
    try:
        return create_engine(url_str)
    except Exception as err:
        raise argparse.ArgumentTypeError(err)

# db_engine ()


def requests_timeout(timeout):
    if timeout is None:
        return None

    try:
        timeout = tuple(float(t) for t in timeout.split(':'))
    except ValueError as err:
        raise argparse.ArgumentTypeError(err)

    if len(timeout) > 2:
        raise argparse.ArgumentTypeError('Invalid timeout.')
    elif len(timeout) == 1:
        timeout = timeout[0]

    return timeout

# requests_timeout ()


def model_config(config_dict):
    """
    Validate the model parameter configration dictionary. Exclusively checks if
    the :code:`dict` is JSON serializable.

    :param str config_dict: Configuration dictionary
    :retval: dict
    """
    try:
        config_dict = json.loads(config_dict)
    except Exception:
        raise argparse.ArgumentTypeError(
            'Invalid model default configuration dictionary syntax.')

    return config_dict

# model_config ()


def wkt(wkt_geom):
    gdal.UseExceptions()
    try:
        geom = ogr.CreateGeometryFromWkt(wkt_geom)
        if not geom:
            raise ValueError('Error while parsing WKT.')
    except Exception as err:
        raise argparse.ArgumentTypeError(
            'Cannot create geometry from WKT: {}'.format(err))

    return geom.ExportToIsoWkt()

# wkt ()


# -----------------------------------------------------------------------------
class WorkerClient(object):
    """
    A synchronous worker client implementation

    Concrete implementations are intended to create
    :cls:`ramsis.utils.protocol.WorkerInputMessage` and start a worker's
    task. The client then polls for the response.

    :param str url: The worker's url.
    :param :cls:`ramsis.util.WorkerInputMessage` data: The data transferred to
    the worker.
    :param int polling_timeout: Timeout while polling for worker results.
    """
    LOGGER = 'ramsis.worker.worker_client'
    SERIALIZER_CONTEXT = {'application': 'SFMWORKER'}

    class WorkerClientError(Error):
        """Base worker client error ({})."""

    class InvalidURL(WorkerClientError):
        """Invalid URL ({})."""

    class InvalidResponse(WorkerClientError):
        """Invalid response ({})."""

    class ConnectionError(WorkerClientError):
        """Failed connecting to worker {!r} ({})."""

    class TimoutError(WorkerClientError):
        """Timout, Failed to retreive worker result data."""

    class WorkerError(WorkerClientError):
        """Worker error for worker {!r} ({}) (Message: {})."""

    def __init__(self, url, data, polling_timeout=60):
        self.data = data
        self._result = None
        self._polling_timeout = polling_timeout

        try:
            self.url = urlparse(url)
        except ValueError as err:
            raise self.InvalidURL(err)

        self.logger = logging.getLogger(self.LOGGER)

    # __init__ ()

    @property
    def result(self):
        return self._result

    @property
    def payload(self):
        serializer = SFMWorkerInputMessageSchema(
            context=self.SERIALIZER_CONTEXT)
        return serializer.dump(self.data).data

    # payload

    def run(self):
        """
        Make the client communicating with the worker. Execution is performed
        synchronously.
        """
        self._request(self.payload)
        self._result = self._poll(polling_timeout=self._polling_timeout)

    # run ()

    def _request(self, payload, timeout=10):
        """
        Template function computing a results for a model (i.e. sending a
        request to the worker).

        :param dict payload: Data send to the worker.
        :param int timeout: Timeout
        """
        url = self.url.geturl()
        self.logger.info('Sending request to worker {} ...'.format(url))
        try:
            response = requests.post(url, json=payload, timeout=timeout)
        except requests.exceptions.RequestException as err:
            raise self.ConnectionError(url, err)
        else:
            if response.status_code != StatusCode.TaskAccepted.value:
                raise self.WorkerError(url, response.status_code,
                                       response.text)

    # _request ()

    def _poll(self, polling_interval=5, polling_timeout=60, request_timeout=5):
        """
        Template function polling for the workers' results.

        :param int polling_interval: The polling interval
        :param int polling_timeout: The polling timeout
        :param int request_timeout: The request_timeout
        """
        timestamp_timeout = (datetime.datetime.utcnow() +
                             datetime.timedelta(seconds=polling_timeout))
        url = self.url.geturl()
        while True:
            if datetime.datetime.utcnow() >= timestamp_timeout:
                raise self.TimoutError()

            response = requests.get(url, timeout=request_timeout)
            if response.status_code == StatusCode.TaskCompleted.value:
                self.logger.info('Worker completed successfully.')
                try:
                    return response.json()
                except ValueError as err:
                    raise self.InvalidResponse(err)

            elif (response.status_code in
                  (StatusCode.TaskCurrentlyProcessing.value,
                   StatusCode.PreviousTaskNotCompleted.value)):
                time.sleep(polling_interval)
            else:
                raise self.WorkerError(url, response.status_code,
                                       response.text)

    # _poll ()

    def __call__(self):
        """alias"""
        self.run()

# class WorkerClient


# -----------------------------------------------------------------------------
class WorkerClientApp(object):
    """
    A *RT-RAMSIS* worker webservice test implementation. For testing purposes.
    """
    VERSION = __version__

    def __init__(self, log_id='RAMSIS'):
        self.parser = None
        self.args = None
        self.log_id = log_id
        self.logger = None
        self.logger_configured = False

    # __init__ ()

    def configure(self, capture_warnings=True):
        """
        Configure the application.

        :param bool capture_warnings: Capture warnings.
        """
        self.parser = self.build_parser(parents=[])

        self.args = self.parser.parse_args()

        self._setup_logger()
        if not self.logger_configured:
            self.logger = logging.getLogger()
            self.logger.addHandler(logging.NullHandler())

        logging.captureWarnings(capture_warnings)

        return self.args

    # configure ()

    def build_parser(self, parents=[]):
        """
        Set up the commandline argument parser.

        :param list parents: list of parent parsers
        :returns: parser
        :rtype: :py:class:`argparse.ArgumentParser`
        """
        parser = CustomParser(
            prog="ramsis-client",
            description='Communicate with *RT-RAMSIS* workers.',
            parents=parents)

        # TODO TODO TODO
        # TODO(damb): Work with subparsers.
        # subcommands are:
        # * commit -> issue a new task/scenario
        # * list -> fetch the tasks for a certain ID; if no ID is passed
        # * remove -> delete a task
        # * cycle -> issue a new task and fetch/ poll for the results; when the
        #   results are fetched the task is removed again

        # optional arguments
        parser.add_argument('--version', '-V', action='version',
                            version='%(prog)s version ' + self.VERSION)
        parser.add_argument('--logging-conf', dest='path_logging_conf',
                            metavar='LOGGING_CONF', type=real_file_path,
                            help="Path to a logging configuration file.")
        parser.add_argument('--timeout', '-t', dest='timeout',
                            type=requests_timeout, default=None,
                            help=('Maximum time to wait for worker response. '
                                  'When passing both a connection timeout and '
                                  'a read timeout values must be colon '
                                  'separated (default: wait forever). For '
                                  'further information see: '
                                  'http://docs.python-requests.org/en/master/'
                                  'user/advanced/#timeouts'))

        subparsers = parser.add_subparsers(help='COMMANDS', dest='cmd',
                                           title='COMMANDS')
        # subparser: commit
        subparser = subparsers.add_parser('commit',
                                          description=self.do_commit.__doc__,
                                          help=('Issue a new task to a '
                                                '*RT-RAMSIS* worker.'))
        # subparser - commit: optional arguments
        subparser.add_argument('--fdsnws-event', dest='url_fdsnws_event',
                               # TODO(damb): Verify the URL
                               type=str, metavar='URL',
                               help=('Fetch a seismic catalog from a '
                                     'fdsnws-event webservice specified by '
                                     'URL directly.'))
        subparser.add_argument('--model-parameters', metavar='DICT',
                               type=model_config, dest='model_parameters',
                               default='{}',
                               help=("Model configuration parameter dict "
                                     "(JSON syntax)."))
        subparser.add_argument('--reservoir', metavar='WKT',
                               type=wkt, dest='reservoir',
                               help=("Reservoir description in WKT format "
                                     "(srid=4326)."))
        # subparser.add_argument('--project', dest='project', metavar='ID',
        #                       type=int, default=1,
        #                       help=('Project identifier. '
        #                             '(default: %(default)s)'))

        # subparser: commit: positional arguments
        # subparser.add_argument('url_db', metavar='URL_DB', type=db_engine,
        #                       help=('RAMSIS datamodel DB URL indicating the '
        #                             'database dialect and connection '
        #                             'arguments.'))
        subparser.add_argument('url_worker', metavar='URL_WORKER',
                               type=url_worker,
                               help='Base worker URL.')
        subparser.add_argument('model', metavar='MODEL', type=str,
                               help='Model identifier.')
        subparser.set_defaults(func=self.do_commit)

        # subparser: list
        subparser = subparsers.add_parser('list',
                                          description=self.do_list.__doc__,
                                          help=('List tasks from a '
                                                '*RT-RAMSIS* worker.'))
        # subparser - list: optional arguments
        subparser.add_argument('--all', '-a', dest='filters',
                               action='append_const', const=None,
                               default=['status_code=200'],
                               help=('Show all tasks (default just '
                                     'successfully completed tasks.'))
        subparser.add_argument('--filter', '-f', dest='filters',
                               action='append',
                               help=('Filter tasks based on conditions '
                                     'provided. The filtering flag format '
                                     'is a key=value pair.'))
        subparser.add_argument('--quiet', '-q', dest='quiet',
                               action='store_true', default=False,
                               help='Only display task identifiers.')
        # subparser - list: positional arguments
        subparser.add_argument('url_worker', metavar='URL_WORKER',
                               type=url_worker,
                               help='Base worker URL.')
        subparser.add_argument('model', metavar='MODEL', type=str,
                               help='Model identifier.')
        subparser.set_defaults(func=self.do_list)

        # subparser: remove
        subparser = subparsers.add_parser('remove',
                                          description=self.do_remove.__doc__,
                                          help=('Remove tasks from a '
                                                '*RT-RAMSIS* worker.'))
        # subparser - remove: positional arguments
        subparser.add_argument('url_worker', metavar='URL_WORKER',
                               type=url_worker,
                               help='Base worker URL.')
        subparser.add_argument('model', metavar='MODEL', type=str,
                               help='Model identifier.')
        subparser.add_argument('task_ids', metavar='TASK_ID', type=uuid.UUID,
                               nargs='+',
                               help='Task to be removed.')
        subparser.set_defaults(func=self.do_remove)

        return parser

    # build_parser

    def run(self):
        """
        Run application.
        """
        exit_code = ExitCode.EXIT_SUCCESS.value
        try:
            self.args.func(self.args)

            """
            # XXX(damb): Load a project from the DB such we avoid setting up a
            # new project from scratch.
            with session_scope(
                    sessionmaker(bind=self.args.db_engine)) as session:
                # load project
                try:
                    project = session.query(Project).\
                        filter(Project.id == self.args.project).\
                        one()
                except (NoResultFound, MultipleResultsFound) as err:
                    raise InvalidProjectId(err)

                self.logger.info('Using project {!r}.'.format(project))

                forecast = self._create_forecast(datetime.datetime.utcnow())
                # append the project's seismic catalog to the forecast_input
                forecast.input.input_catalog = \
                    project.seismic_catalog
                forecast.input.input_catalog.catalog_date = \
                    datetime.datetime.utcnow()
                reference_point = project.reference_point
                injection_well = project.injection_well
                injection_history = project.injection_history

                model_parameters = {'x': 4.4}

                data = WorkerInputMessage(
                    forecast=forecast,
                    coordinate_reference=reference_point,
                    injection_well=injection_well,
                    injection_history=injection_history,
                    model_parameters=model_parameters)

                client = WorkerClient("http://localhost:5000/runs",
                                      data=data, )
                client()
                self.logger.info('Worker message: {!r}'.format(client.result))
                """

        except Error as err:
            self.logger.error(err)
            exit_code = ExitCode.EXIT_ERROR.value
        except Exception as err:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.logger.critical('Local Exception: %s' % err)
            self.logger.critical('Traceback information: ' +
                                 repr(traceback.format_exception(
                                     exc_type, exc_value, exc_traceback)))
            exit_code = ExitCode.EXIT_ERROR.value

        sys.exit(exit_code)

    # run ()

    def do_commit(self, args):
        """
        Issue a new task to a *RT-RAMSIS* worker. The task is created from an
        already existing project from the RT-RAMSIS database.
        """
        def quakeml(args):

            if args.url_fdsnws_event:
                self.logger.debug(
                    'Fetching seismic catalog from fdsnws-event: {!r}'.format(
                        args.url_fdsnws_event))
                resp = requests.get(args.url_fdsnws_event)
                qml = resp.content
                self.logger.debug('Received seismic catalog.')
            else:
                # TODO(damb): To be done.
                raise NotImplementedError(
                    'Fetching the catalog from the ramsis-core DB '
                    'is currently not implemented.')

            return qml

        # quakeml ()

        def model_parameters(args):

            if args.model_parameters:
                self.logger.debug(
                    'Use user-defined model parameters: {!r}'.format(
                        args.model_parameters))

            # TODO(damb): Fetching the model configuration from the ramsis-core
            # DB is currently not implemented.

            return args.model_parameters

        # model_parameters ()

        def reservoir(args):

            if args.reservoir:
                self.logger.debug(
                    'Use user-defined reservior configuration: {!r}'.format(
                        args.reservoir))

            # TODO(damb): Fetching the reservoir configuration from the
            # ramsis-core DB is currently not implemented.

            return args.reservoir

        # reservoir ()

        data = {
            'seismic_catalog': quakeml(args),
            'model_parameters': model_parameters(args),
            'reservoir': reservoir(args)
        }

        payload = RemoteSeismicityWorkerHandle.Payload(
            **data, well=None, scenario=None)

        worker = RemoteSeismicityWorkerHandle.create(
            base_url=self.args.url_worker,
            worker_id=self.args.model,
            timeout=self.args.timeout)

        self.logger.debug('SeismicityWorker handle: {}'.format(worker))

        worker.compute(payload)

    # do_commit ()

    def do_list(self, args):
        """
        List tasks from a *RT-RAMSIS* worker.
        """
        def fconds_as_dict(filter_conds):
            retval = {}
            for f_cond in filter_conds:
                f = f_cond.split('=')
                if len(f) != 2:
                    raise AppError(
                        'Invalid filter condition ({})'.format(f_cond))
                retval[f[0]] = f[1]
            return retval

        # fconds_as_dict ()

        def extract_task_ids(filter_conds):
            if 'id' not in filter_conds:
                return []

            return filter_conds.pop('id').split(',')

        # extract task_ids

        self.logger.debug('Worker base URL: {}'.format(self.args.url_worker))
        self.logger.debug('Worker model: {}'.format(self.args.model))

        worker = RemoteSeismicityWorkerHandle.create(
            base_url=self.args.url_worker,
            worker_id=self.args.model,
            timeout=self.args.timeout)

        self.logger.debug('SeismicityWorker handle: {}'.format(worker))

        filter_conditions = {}

        if None not in self.args.filters:
            filter_conditions = fconds_as_dict(self.args.filters)

        self.logger.debug('Filters: {}'.format(filter_conditions))

        resp = worker.query(extract_task_ids(filter_conditions))
        self.logger.debug('Number of query results: {}'.format(resp.count()))

        if self.args.quiet:
            for r in resp.filter_by(**filter_conditions).all():
                print(list(r['data'].keys())[0])
        else:
            print('{:<40}{:<12}{:<20}{:<8}{:<60} {:<20}'.format(
                  'TASK_ID', 'STATUS_CODE', 'STATUS', 'LENGTH', 'DATA',
                  'WARNING'))
            for r in resp.filter_by(**filter_conditions).all():
                print(('{task_id:<40}{status_code:<12}{status:<20}'
                       '{length:<8}{result:<60} {warning:<20}').format(
                    task_id=list(r['data'].keys())[0],
                    result=str(list(r['data'].values())), **r))

    # do_list ()

    def do_remove(self, args):
        """
        Remove one or more tasks from a *RT-RAMSIS* worker.
        """
        self.logger.debug('Worker base URL: {}'.format(self.args.url_worker))
        self.logger.debug('Worker model: {}'.format(self.args.model))

        worker = RemoteSeismicityWorkerHandle.create(
            base_url=self.args.url_worker,
            worker_id=self.args.model,
            timeout=self.args.timeout)

        self.logger.debug('SeismicityWorker handle: {}'.format(worker))

        resp = worker.delete(self.args.task_ids)
        self.logger.debug('Number of tasks removed: {}'.format(resp.count()))

        for r in resp.all():
            print(list(r['data'].keys())[0])

    # do_delete ()

    def _setup_logger(self):
        """
        Initialize the logger of the application.
        """
        if self.args.path_logging_conf:
            try:
                logging.config.fileConfig(self.args.path_logging_conf)
                self.logger = logging.getLogger()
                self.logger_configured = True
                self.logger.info('Using logging configuration read from "%s"',
                                 self.args.path_logging_conf)
            except Exception as err:
                print('WARNING: Setup logging failed for "%s" with "%s".' %
                      (self.args.path_logging_conf, err), file=sys.stderr)
                self._setup_fallback_logger()
                self.logger.warning('Setup logging failed with %s. '
                                    'Using fallback logging configuration.' %
                                    err)
    # _setup_logger ()

    def _setup_fallback_logger(self):
        """setup a fallback logger"""
        # NOTE(damb): Provide fallback syslog logger.
        self.logger = logging.getLogger()
        fallback_handler = logging.handlers.SysLogHandler('/dev/log',
                                                          'local0')
        fallback_handler.setLevel(logging.WARN)
        fallback_formatter = logging.Formatter(
            fmt=("<" + self.log_id +
                 "> %(asctime)s %(levelname)s %(name)s %(process)d "
                 "%(filename)s:%(lineno)d - %(message)s"),
            datefmt="%Y-%m-%dT%H:%M:%S%z")
        fallback_handler.setFormatter(fallback_formatter)
        self.logger.addHandler(fallback_handler)
        self.logger_configured = True

    # _setup_fallback_logger ()

# class WorkerClientApp


# ----------------------------------------------------------------------------
def main():
    """
    Main function for SaSS model worker webservice
    """

    app = WorkerClientApp(log_id='RAMSIS-CLIENT')

    try:
        app.configure()
    except AppError as err:
        # handle errors during the application configuration
        print('ERROR: Application configuration failed "%s".' % err,
              file=sys.stderr)
        sys.exit(ExitCode.EXIT_ERROR.value)

    return app.run()

# main ()


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    main()

# ---- END OF <client.py> ----
