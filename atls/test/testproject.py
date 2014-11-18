# -*- encoding: utf-8 -*-
"""
Unittest for the Project class

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest

from PyQt4 import QtCore
from mock import MagicMock

from data.project.project import Project


class ProjectTest(unittest.TestCase):

    def test_open(self):
        """ There isn't much to test here for now """
        mock_store = MagicMock()
        project = Project(mock_store)
        self.assertIsNotNone(project)

    def test_close(self):
        """ Test if closing the project emits the will_close signal """
        app = QtCore.QCoreApplication([])
        mock_store = MagicMock()
        mock_signal_handler = MagicMock()
        project = Project(mock_store)
        project.will_close.connect(mock_signal_handler)
        project.close()
        app.processEvents()
        mock_signal_handler.assert_called_once_with(project)


if __name__ == '__main__':
    unittest.main()
