# -*- encoding: utf-8 -*-
"""
Tests the store class which provides low level access to the sqlite db.

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
import os
import logging
from mock import MagicMock, patch, call
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, Float, DateTime
from datamodel.base import Base
from datamodel.store import *

DB_FILE = 'test.sqlite'

# Data Model

class EventA(Base):
    # ORM declarations for SQLAlchemy
    __tablename__ = 'a_events'
    id = Column(Integer, primary_key=True)
    date_time = Column(DateTime)
    value = Column(Float)

    def __init__(self, date_time, value):
        self.date_time = date_time
        self.value = value


class EventB(Base):
    # ORM declarations for SQLAlchemy
    __tablename__ = 'b_events'
    id = Column(Integer, primary_key=True)
    date_time = Column(DateTime)
    value = Column(Float)

    def __init__(self, date_time, value):
        self.date_time = date_time
        self.value = value


# Test Fixtures

class OpenStore(unittest.TestCase):
    """ Tests basic store creation and opening / closing sessions """

    def setUp(self):
        """ We start out with an empty db """
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        self.store = Store('sqlite:///' + DB_FILE)

    def tearDown(self):
        """ Close and delete the test store """
        self.store.close()
        os.remove(DB_FILE)

    def test_db_creation(self):
        """ Test that the store is created and empty """
        self.assertTrue(os.path.exists(DB_FILE))
        self.assertIsNotNone(self.store.engine)
        tables = self.store.engine.table_names()
        self.assertListEqual(tables, [EventA.__tablename__,
                                      EventB.__tablename__])

    def test_database_reopen(self):
        """ Test that data still exists after reopening a store """
        an_event = EventA(datetime.now(), 1)
        self.store.add([an_event])
        self.store.close()
        self.store = Store('sqlite:///' + DB_FILE)
        content = self.store.read_all(EventA)
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0].value, 1)


class ReadingAndWriting(unittest.TestCase):
    """ Tests basic reading and writing from the store """

    def setUp(self):
        """ We start out with one A and two Bs """
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        self.store = Store('sqlite:///' + DB_FILE)
        date = datetime.now()
        a_list = [EventA(date + timedelta(seconds=1), 1)]
        b_list = [EventB(date + timedelta(seconds=2), 2),
                  EventB(date + timedelta(seconds=3), 3)]
        self.store.add(a_list)
        self.store.add(b_list)

    def tearDown(self):
        """ Close and delete the test store """
        self.store.close()
        os.remove(DB_FILE)

    def test_basic_reading(self):
        """ Test basic reading """
        all_bs = self.store.read_all(EventB)
        self.assertEqual(len(all_bs), 2)
        b1 = self.store.read_first(EventB, order='date_time')
        self.assertEqual(b1.value, 2)
        b2 = self.store.read_last(EventB, order='date_time')
        self.assertEqual(b2.value, 3)

    def test_predicate_reading(self):
        """ Test reading with predicates """
        predicate = (3 == EventB.value)
        b2_list = self.store.read_all(EventB, predicate)
        self.assertEqual(len(b2_list), 1)
        self.assertEqual(b2_list[0].value, 3)
        b1 = self.store.read_first(EventB, predicate, order='date_time')
        self.assertEqual(b1.value, 3)
        predicate = (2 == EventB.value)
        b2 = self.store.read_last(EventB, predicate, order='date_time')
        self.assertEqual(b2.value, 2)

    def test_counting(self):
        """ Test object counting """
        count_a = self.store.count(EventA)
        count_b = self.store.count(EventB)
        self.assertEqual(count_a, 1)
        self.assertEqual(count_b, 2)
        predicate = (3 == EventB.value)
        count_b = self.store.count(EventB, predicate)
        self.assertEqual(count_b, 1)

    def test_predicate_reading(self):
        """
        Test if the store successfully determines the order attribute
        from the read cache

        """
        self.store.init_sequential_read_cache(EventB, 'date_time', 5)
        b = self.store.read_last(EventB)
        self.assertEqual(b.value, 3)


class ReadCached(unittest.TestCase):
    """ Test sequential read cache (standalone) """

    def setUp(self):
        """
        We replace the __getitem__ method of the query object since this is
        what the cache calls when it needs to fetch a new slice of data from
        the store

        """
        def getitem(a_slice):
            events = []
            indices = a_slice.indices(1000)
            for idx in range(indices[0], indices[1]):
                events.append(EventA(datetime.now(), idx))
            return events

        session_mock = MagicMock()
        query = MagicMock()
        query.__getitem__.side_effect = getitem
        query.order_by.return_value = query
        session_mock.query.return_value = query
        self.cache = SequentialReadCache(session_mock, EventA, 'date_time', 5)

    def test_cache_access(self):
        """ Test that the store is accessed hit when needed """

        for i in range(12):
            event = self.cache[i]
            self.assertEqual(event.value, i)

        expected = [call(slice(0, 5, None)), call(slice(5, 10, None)),
                    call(slice(10, 15, None))]
        self.assertListEqual(self.cache.query.__getitem__.mock_calls, expected)

    def test_cache_reset(self):
        """ Test that the cache re-accesses the store after a reset """
        event = self.cache[3]
        self.assertEqual(event.value, 3)
        self.cache.invalidate()
        event = self.cache[3]
        self.assertEqual(event.value, 3)

        expected = [call(slice(0, 5, None)), call(slice(0, 5, None))]
        self.assertListEqual(self.cache.query.__getitem__.mock_calls, expected)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.info('running store tests....')
    unittest.main()
