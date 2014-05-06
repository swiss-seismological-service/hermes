# -*- encoding: utf-8 -*-
"""
Main file

The Main file sets up the user interface and bootstraps the application

"""

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
    atls = Atls()
    atls.run()


if __name__ == "__main__":
    main()