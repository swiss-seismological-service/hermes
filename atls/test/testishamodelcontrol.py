# -*- encoding: utf-8 -*-
"""
Short Description

Long Description

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from datetime import datetime
from time import sleep

from PyQt4 import QtCore
from mock import MagicMock, call

from core.ismodelcontrol import DetachedRunner
from core.ismodels.common import ModelInput, Model, ModelState


class MockIshaModel(Model):
    """
    Mock ISHA Model that the model_controller under test controls. Does
    nothing except emitting the finished signal.

    """

    def _do_run(self):
        return self


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
        on_finished = MagicMock()
        on_state_changed = MagicMock()
        self.mock_model.state_changed.connect(on_state_changed)
        self.mock_model.finished.connect(on_finished)
        dummy_run_data = ModelInput(datetime.now())
        self.detached_runner.run_model(dummy_run_data)
        # Wait until the model thread emits its signals. This is a bit fragile
        # since event delivery from the model thread might take longer
        sleep(0.2)
        self.app.processEvents()
        on_finished.assert_called_once_with(self.mock_model)
        expected_calls = [call(ModelState.RUNNING), call(ModelState.IDLE)]
        on_state_changed.assert_has_calls(expected_calls)


if __name__ == '__main__':
    unittest.main()
