# -*- encoding: utf-8 -*-
"""
Main file

The Main file sets up the user interface and bootstraps the application

"""

import argparse

# We use API v2 for Qt objects, since they make working with variants easier
# and are more future proof (v2 is default in python 3).
# This needs to be done before we import PyQt4
import sip
sip.setapi(u'QDate', 2)
sip.setapi(u'QDateTime', 2)
sip.setapi(u'QString', 2)
sip.setapi(u'QTextStream', 2)
sip.setapi(u'QTime', 2)
sip.setapi(u'QUrl', 2)
sip.setapi(u'QVariant', 2)

from atls import Atls


def main():
    """
    Launches Atls i.s.

    Creates the Atls top level object and passes control to it.

    """

    parser = argparse.ArgumentParser(description='Adaptive Traffic Light '
                                                 'System')
    parser.add_argument('-n', '--nogui', action='store_true',
                        help='runs ATLS without a GUI and starts simulation '
                             'immediately')
    parser.add_argument("-v", "--verbosity", type=int, choices=[0, 1, 2, 3],
                        default=1, help="output verbosity (0-3, default 1)")
    parser.add_argument('-c', '--config', meta='CONFIG_FILE',
                        help='config file to read')

    args = parser.parse_args()


    atls = Atls()
    atls.run()

if __name__ == "__main__":
    main()