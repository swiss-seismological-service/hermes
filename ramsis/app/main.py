# -*- encoding: utf-8 -*-
"""
Main file

The Main file sets up the user interface and bootstraps the application

"""

import argparse
import logging


from ramsis import Ramsis


def main():
    """
    Launches Ramsis i.s.

    Creates the Ramsis top level object and passes control to it.

    """

    parser = argparse.ArgumentParser(description='Adaptive Traffic Light '
                                                 'System')
    parser.add_argument('-n', '--no-gui', action='store_true',
                        help='runs RAMSIS without a GUI')
    parser.add_argument("-v", "--verbosity", type=int, choices=[0, 1, 2],
                        default=1, help="output verbosity (0-2, default 0)")
    parser.add_argument('-c', '--config', metavar='CONFIG_FILE',
                        help='config file to read when launched with --no-gui '
                             '(default: ramsis.ini)')

    args = parser.parse_args()

    # Additional sanity checks
    if args.no_gui is True and args.config is None:
        parser.error("--no-gui requires --config")

    configure_logging(args.verbosity)
    ramsis = Ramsis(args)
    ramsis.run()


def configure_logging(verbosity):
    """
    Configures and the root logger.

    All loggers in submodules will automatically become children of the root
    logger and inherit some of the properties.

    """
    lvl_lookup = {
        0: logging.WARN,
        1: logging.INFO,
        2: logging.DEBUG
    }
    root_logger = logging.getLogger()
    root_logger.setLevel(lvl_lookup[verbosity])
    formatter = logging.Formatter('%(asctime)s %(levelname)s: '
                                  '[%(name)s] %(message)s')
    # ...handlers from 3rd party modules - we don't like your kind here
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
    # ...setup console logging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


if __name__ == "__main__":
    main()
