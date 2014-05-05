# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from datetime import datetime
from PyQt4 import QtCore
from mock import MagicMock
from ishamodelcontrol import DetachedRunner
from isha.common import RunInput, Model


from time import sleep

class MockIshaModel(Model):
    """
    Mock ISHA Model that the model_controller under test controls. Does
    nothing except emitting the finished signal.

    """

    def run(self):
        super(MockIshaModel, self).run()
        self.finished.emit(self)


class DetachedRunnerTest(unittest.TestCase):

    def setUp(self):
        """
        We need to setup a QCoreApplication because the QThread stuff expects
        an event loop to be present. Since we never start the event loop we
        need to process events manually.

        """
        self.app = QtCore.QCoreApplication([])
        self.mock_model = MockIshaModel()
        self.detached_runner = DetachedRunner(self.mock_model)

    def test_initialization(self):
        """ Make sure the model is not associated with the main thread """
        this_thread = QtCore.QThread.currentThread()
        self.assertNotEqual(this_thread, self.mock_model.thread())

    def test_start_finish(self):
        """ Check if the model starts and terminates as expected """
        finished_slot = MagicMock()
        self.mock_model.finished.connect(finished_slot)
        dummy_run_data = RunInput(datetime.now())
        self.detached_runner.run_model(dummy_run_data)
        # Wait until the model thread emits its signals. This is a bit fragile
        # since event delivery from the model thread might take longer
        sleep(0.2)
        self.app.processEvents()
        finished_slot.assert_called_once_with(self.mock_model)


if __name__ == '__main__':
    unittest.main()
