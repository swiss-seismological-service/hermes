# -*- encoding: utf-8 -*-
"""
Short Description

Long Description

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from time import sleep

from PyQt4 import QtCore
from mock import MagicMock

from core.runners import HYDWSRunner


def mock_run():
    return None


class HYDWSRunnerTest(unittest.TestCase):

    def setUp(self):
        """
        We need to setup a QCoreApplication because the QThread stuff expects
        an event loop to be present. Since we never start the event loop we
        need to process events manually.

        """
        self.app = QtCore.QCoreApplication([])
        self.hydws_runner = HYDWSRunner(None)
        self.hydws_runner._importer._run = mock_run

    def test_initialization(self):
        """ Make sure the importer is not associated with the main thread """
        this_thread = QtCore.QThread.currentThread()
        self.assertNotEqual(this_thread, self.hydws_runner._importer.thread())

    def test_start_finish(self):
        """ Check if the importer starts and terminates as expected """
        on_finished = MagicMock()
        self.hydws_runner._importer.finished.connect(on_finished)
        self.hydws_runner.start()
        # Wait until the model thread emits its signals. This is a bit fragile
        # since event delivery from the model thread might take longer
        sleep(0.2)
        self.app.processEvents()
        on_finished.assert_called_once_with(None)


if __name__ == '__main__':
    unittest.main()
