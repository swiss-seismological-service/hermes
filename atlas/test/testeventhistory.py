# -*- encoding: utf-8 -*-
"""
Tests the EventHistory class
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from model.eventhistory import EventHistory
import sqlalchemy
from sqlalchemy import Column, Float, DateTime
import unittest
from datetime import datetime, timedelta
from mock import Mock, MagicMock

NUM_TEST_EVENTS = 10


class Event():
    """ A dummy event class for testing """

    date_time = Column(DateTime)  # required for predicate definitions
    value = Column(Float)         # required for predicate definitions

    def __init__(self, date_time, value):
        self.date_time = date_time
        self.value = value


class MockStore(MagicMock):
    """ A mock store class to inject into the history for testing """

    def __init__(self, test_content=None):
        """
        Initialize Mock store.

        Provide the test content in the named argument 'test_content'

        """
        super(MockStore, self).__init__()
        self.test_content = test_content

        if test_content is None:
            return

        # Read function for mock store
        def store_read(entity, index, predicate=None, order=None):
            return self.test_content[index]

        self.count = Mock(return_value=len(self.test_content))
        self.read = Mock(side_effect=store_read)
        self.read_all = Mock(return_value=self.test_content)
        self.read_last = Mock(return_value=self.test_content[-1])

    def _get_child_mock(self, **kw):
        """
        If this is not implemented, the superclass will attempt to create child
        mocks of class MockStore which fails since it can't provide test_content

        """
        return MagicMock(**kw)


class BasicOperation(unittest.TestCase):
    """ Tests basic operation such as reading and writing to the history """

    def setUp(self):
        """
        Create test content and a mock store to provide the content to the
        history under test

        """

        # Test content
        self.date = datetime.now()
        test_content = []
        for i in range(NUM_TEST_EVENTS):
            test_content.append(Event(self.date + timedelta(seconds=i), i))
        self.test_content = test_content

        self.mock_store = MockStore(test_content)
        self.history = EventHistory(self.mock_store, Event)

    def test_read_cache_creation(self):
        """ Check if sequential read cache is created on initialisation """
        self.mock_store.init_sequential_read_cache.\
            assert_called_once_with(Event, 'date_time')

    def test_counting(self):
        """ Counting elements in history """
        self.assertEqual(len(self.history), NUM_TEST_EVENTS)

    def test_indexed_reading(self):
        """ Reading through __getitem__ """
        event = self.history[3]
        self.assertEqual(event.value, 3)

    def test_reading_latest(self):
        """ Reading the latest event """
        event = self.history.latest_event()
        self.assertEqual(event.value, NUM_TEST_EVENTS - 1)
        max_time = self.date + timedelta(seconds=4.5)
        event = self.history.latest_event(max_time)
        entity, predicate = self.mock_store.read_last.call_args
        # It's difficult to test the content of the predicate since there
        # might be different ways the history could do this. So we just check
        # if there is a predicate at all.
        self.assertIsNotNone(predicate)

    def test_read_specific_time_interval(self):
        """ Read events in specific time interval """
        earliest = self.date + timedelta(seconds=2.1)
        latest = self.date + timedelta(seconds=5.9)
        events = self.history.get_events_between(earliest, latest)
        args, kwargs = self.mock_store.read_all.call_args
        entity, predicate = args
        # It's difficult to test the content of the predicate since there
        # might be different ways the history could do this. So we just check
        # if there is a predicate at all.
        self.assertIsNotNone(predicate)


if __name__ == '__main__':
    unittest.main()
