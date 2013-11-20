# -*- encoding: utf-8 -*-
"""
Unit test for the IshaModelController

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from PyQt4 import QtCore
from mock import MagicMock
from model.ishamodel import IshaModelController, IshaModelParameters, IshaModel


class MockIshaModel(IshaModel):
    """
    Mock ISHA Model that the model_controller under test controls. Does
    nothing except emitting the finished signal.

    """

    def run(self):
        self.finished.emit()


class MyTestCase(unittest.TestCase):

    def setUp(self):
        """
        We need to setup a QCoreApplication because the QThread stuff expects
        an event loop to be present. We never start the event loop however and
        thus need to process events manually.

        """
        self.app = QtCore.QCoreApplication([])
        self.mock_model = MockIshaModel()
        self.model_controller = IshaModelController(self.mock_model)

    def test_initialization(self):
        """ Make sure the model is not associated with the main thread """
        this_thread = QtCore.QThread.currentThread()
        self.assertNotEqual(this_thread, self.mock_model.thread())

    def test_start_finish(self):
        """ Check if the model starts and terminates as expected """
        finished_slot = MagicMock()
        self.mock_model.finished.connect(finished_slot)
        dummy_info = IshaModelParameters()
        self.model_controller.start_forecast(dummy_info)
        # wait until the model thread emits its signals
        while self.app.hasPendingEvents() is False:
            pass
        self.app.processEvents()
        finished_slot.assert_called_once_with()




if __name__ == '__main__':
    unittest.main()
