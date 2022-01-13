#!/usr/bin/env python3
# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Utility to import data into the RAMSIS DB.
"""

import argparse
import logging
import logging.config
import logging.handlers
import sys

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from ramsis.datamodel.forecast import Forecast  # noqa
from ramsis.datamodel.hydraulics import Hydraulics  # noqa
from ramsis.datamodel.project import Project  # noqa
from ramsis.datamodel.seismicity import SeismicityModelRun  # noqa
from ramsis.datamodel.status import Status  # noqa
from ramsis.utils.app import CustomParser, AppError
from ramsis.utils.error import ExitCode
from ramsis.io.seismics import QuakeMLObservationCatalogDeserializer


def url(url):
    """
    check if SQLite URL is absolute.
    """
    if (url.startswith('sqlite:') and not
            (url.startswith('////', 7) or url.startswith('///C:', 7))):
        raise argparse.ArgumentTypeError('SQLite URL must be absolute.')
    return url


class ImportSeismicsAppError(AppError):
    """AppError ({})."""


# -----------------------------------------------------------------------------
class ImportSeismicsApp:
    """
    Import a seismic catalog.
    """
    VERSION = '0.1'

    def __init__(self, log_id='RAMSIS'):
        self.parser = None
        self.args = None
        self.log_id = log_id
        self.logger = None
        self.logger_configured = False

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

    def build_parser(self, parents=[]):
        """
        Set up the commandline argument parser.

        :param list parents: list of parent parsers
        :returns: parser
        :rtype: :py:class:`argparse.ArgumentParser`
        """
        parser = CustomParser(
            prog="ramsis-import-seismics",
            description='Import a seismic catalog.',
            parents=parents)

        # optional arguments
        parser.add_argument('--version', '-V', action='version',
                            version='%(prog)s version ' + self.VERSION)
        parser.add_argument('--logging-conf', dest='path_logging_conf',
                            metavar='LOGGING_CONF',
                            type=argparse.FileType('r'),
                            help="Path to a logging configuration file.")
        parser.add_argument('--force', '-f', action='store_true',
                            default=False,
                            help='Overwrite existing catalog.')
        parser.add_argument('--infile', metavar='PATH',
                            type=argparse.FileType('rb'),
                            default=sys.stdin,
                            help=('Input data file to be parsed '
                                  '(default: stdin).'))

        # positional arguments
        parser.add_argument('project', metavar='PROJECT',
                            type=str,
                            help=('Project the seismic catalog should be '
                                  'attached to.'))
        parser.add_argument('db_url', type=url, metavar='URL',
                            help=('DB URL indicating the database dialect and '
                                  'connection arguments. For SQlite only a '
                                  'absolute file path is supported.'))

        return parser

    def run(self):

        engine = create_engine(self.args.db_url)
        Session = sessionmaker(bind=engine)

        @contextmanager
        def session_scope():
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

        with session_scope() as session:
            try:
                p = session.query(Project).\
                    filter(Project.name == self.args.project).\
                    one()
            except (NoResultFound, MultipleResultsFound) as err:
                raise ImportSeismicsAppError(str(err))

            self.logger.debug(f'Found project {p!r}.')

            if not self.args.force and p.seismiccatalog:
                raise ImportSeismicsAppError(
                    'Found present seimic catalog; use --force|-f to '
                    'overwrite.')

            deserializer = QuakeMLObservationCatalogDeserializer(
                ramsis_proj=p.proj_string,
                external_proj=4326,
                ref_easting=p.referencepoint_x,
                ref_northing=p.referencepoint_y,
                transform_func_name='pyproj_transform_to_local_coords')

            try:
                cat = deserializer.load(self.args.infile)
            except Exception as err:
                raise ImportSeismicsAppError(f"Deserialization Error: {err!r}")

            p.seismiccatalog = cat

            self.logger.info(
                f'Imported seismic catalog {cat!r}.')

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


# ----------------------------------------------------------------------------
def main():

    app = ImportSeismicsApp(log_id='RAMSIS')

    try:
        app.configure()
    except AppError as err:
        # handle errors during the application configuration separately
        print(f'ERROR: Application configuration failed {err!r}.',
              file=sys.stderr)
        sys.exit(ExitCode.EXIT_ERROR.value)

    try:
        return app.run()
    except AppError as err:
        app.logger.critical(f'{err}')
        sys.exit(ExitCode.EXIT_ERROR.value)


if __name__ == '__main__':
    main()
