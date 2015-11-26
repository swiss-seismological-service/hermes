# -*- encoding: utf-8 -*-
"""
Tests the EventHistory class

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from datetime import datetime, timedelta

from sqlalchemy import Column, Float, DateTime
from mock import Mock, MagicMock

from data.project.eventhistory import EventHistory


NUM_TEST_EVENTS = 10


class Event():
    """ A dummy event class for testing """

    date_time = Column(DateTime)  # required for predicate definitions
    value = Column(Float)         # required for predicate definitions

    def __init__(self, date_time, value):
        self.date_time = date_time
        self.value = value

    def __cmp__(self, other):
        return ((self.date_time == other.date_time) and
                (self.value == other.value))


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
        mocks of class MockStore which fails since it can't provide
        test_content

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

    def test_loading_and_counting(self):
        self.assertEqual(len(self.history), 0)
        self.history.reload_from_store()
        self.assertEqual(len(self.history), NUM_TEST_EVENTS)

    def test_indexed_reading(self):
        """ Reading through __getitem__ """
        self.history.reload_from_store()
        event = self.history[3]
        self.assertEqual(event.value, 3)

    def test_reading_latest(self):
        """ Reading the latest event """
        self.history.reload_from_store()
        event = self.history.latest_event()
        self.assertEqual(event.value, NUM_TEST_EVENTS - 1)
        max_time = self.date + timedelta(seconds=4.5)
        event = self.history.latest_event(max_time)
        self.assertEqual(event, self.test_content[-1])

    def test_read_specific_time_interval(self):
        """ Read events in specific time interval """
        self.history.reload_from_store()
        earliest = self.date + timedelta(seconds=2.1)
        latest = self.date + timedelta(seconds=5.9)
        events = self.history.events_between(earliest, latest)
        self.assertListEqual(events, self.test_content[2:5])

    def test_add_retrieve_and_clear(self):
        """ Test adding, retrieving and clearing events """
        for event in self.test_content:
            self.history.add(event)

        idx = NUM_TEST_EVENTS / 2
        date = self.date + timedelta(seconds=idx)
        all_events = self.history.all_events()
        events_before = self.history.events_before(date)
        events_after = self.history.events_after(date)

        self.assertEqual(all_events, self.test_content)
        self.assertEqual(events_before, self.test_content[:idx])
        self.assertEqual(events_after, self.test_content[idx + 1:])

        self.history.clear()
        self.assertEqual(self.history.all_events(), [])


if __name__ == '__main__':
    unittest.main()
