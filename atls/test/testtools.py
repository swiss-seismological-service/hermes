# -*- encoding: utf-8 -*-
"""
Test Atls Tools

Tools are various helpers that are collected in the tools.py file
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
import logging
import tools

class TestAtlsLogger(unittest.TestCase):
    """
    Tests our custom logging class

    """
    def setUp(self):
        logging.NOTICE = 25
        logging.addLevelName(logging.NOTICE, 'NOTICE')
        logging.setLoggerClass(tools.AtlsLogger)

    def test_notice_level(self):
        """ Check if the logger responds to .notice() """
        logger = logging.getLogger('Atls')
        try:
            logger.notice('test log')
        except TypeError:
            self.assertTrue(False, 'Logger does not implement notice()')


if __name__ == '__main__':
    unittest.main()
