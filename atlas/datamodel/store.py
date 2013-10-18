# -*- encoding: utf-8 -*-
"""
Defines the EventStore class which writes and reads event data from a database

"""

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from tools import PageCache
import base


class SequentialReadCache:
    """
    Provides a read cache for improved performance during sequential access.

    The read cache uses a PageCache to fetch objects from the db page wise. This
    reduces db access during sequential access.
    It also manages a query for the entity that it manages and provides
    functions for container type access such as __len__() and __getitem__().

    """

    def __init__(self, session, entity, order_attr):
        self.session = session
        self.entity = entity
        self.order_attr = order_attr
        self.page_cache = PageCache()
        self.query = None
        self.num_events = 0
        self.refresh()

    def refresh(self):
        self.query = self.session.query(self.entity).order_by(self.order_attr)
        self.page_cache.query = self.query
        self.num_events = self.query.count()

    def invalidate(self):
        self.page_cache.invalidate()

    def __len__(self):
        return self.num_events

    def __getitem__(self, item):
        """
        Return the event at the specified index

        :param item: event index (0 being the newest)
        :type item: int
        :rtype: Base

        """
        return self.page_cache[item]


class Store:
    """
    Manages access to the store (database)

    The store uses sqlalchemy to persist event objects to the
    database. As a consequence all objects that need to be persisted
    should inherit from the declarative base provided by :mod:`base`

    A store provides read caches for improved read performance. Caches must
    be created explicitly by calling init_read_cache(entity) where
    entity is the class for which reading should be cached.

    """

    def __init__(self, store_url):
        """
        :param store_url: Database url

        """
        self._engine = create_engine(store_url, echo=False)
        base.Base.metadata.create_all(self._engine, checkfirst=True)
        Session = sessionmaker(bind=self._engine)
        self._read_caches = {}
        self._session = Session()

    def purge(self, entity=None):
        """
        Deletes all data from the store

        If entity is given, only data for this entity will be deleted

        """
        if entity:
            cache = self._read_caches[entity]
            if cache:
                cache.invalidate()
            entity.__table__.delete()
        else:
            base.Base.metadata.drop_all(bind=self._engine)
            base.Base.metadata.create_all(self._engine)

    def commit(self):
        """
        Commits pending changes to the store immediately

        """
        self._session.commit()

    def close(self):
        self._session.close()


    # Reading and Writing

    def add(self, objects):
        """
        Convenience method to add and commit new objects to the store.

        :param objects: A list of objects
        :type event: List of 'Base' derived objects

        """
        self._session.add_all(objects)
        self.commit()

        # if we have a read cache for this class, we need to refresh it now
        cache = self._read_caches[objects[0].__class__]
        if cache:
            cache.invalidate()
            cache.refresh()

    def _get_read_query(self, entity, predicate):
        # get the query from the sequential read cache if we have one for
        # this entity. otherwise create a new query.
        cache = self._read_caches[entity]
        query = None
        if cache:
            query = cache.query
        else:
            query = self.session.query(entity)

        if predicate:
            query = query.filter(predicate)

        return query

    def read_first(self, entity, predicate=None, order_attr=None):
        """
        Read and return the first object from the store that meets the
        predicate provided by the caller. The attribute provided in order_attr
        is used to determine the sort order.
        If the store has a sequential read cache for the entity (see
        init_sequential_read_cache() the order_attr will be determined from
        there.

        :param entity: Class of the object to read
        :param predicate: List of logical criteria, e.g. (Event.date < a_date,
            Event.id > 10)
        :type predicate: list
        :param order_attr: attribute that determines the sort order. Optional
            if the store has a read cache for the entity.
        :type order_attr: string
        :rtype: list

        """
        query = self._get_read_query(entity, predicate)

        # order_attr given in parameter list overrides any other order attribute
        if order_attr:
            query = query.order_by(None)
            query = query.order_by(order_attr)

        return query.first()

    def read_last(self, entity, predicate=None, order_attr=None):
        """
        Read and return the last object from the store that meets the
        predicate provided by the caller. The attribute provided in order_attr
        is used to determine the sort order.
        If the store has a sequential read cache for the entity (see
        init_sequential_read_cache() the order_attr will be determined from
        there.

        :param entity: Class of the object to read
        :param predicate: List of logical criteria, e.g. (Event.date < a_date,
            Event.id > 10)
        :type predicate: list
        :param order_attr: attribute that determines the sort order. Optional
            if the store has a read cache for the entity.
        :type order_attr: string
        :rtype: list

        """
        query = self._get_read_query(entity, predicate)

        cache = self._read_caches[entity]
        if cache:
            order_attr = order_attr if order_attr else cache.order_attr

        # revert order
        query = query.order_by(None)
        query = query.order_by(desc(order_attr))

        return query.first()

    def read_all(self, entity, predicate=None, order_attr=None):
        """
        Read and return all objects from the store that meet the predicate
        provided by the caller

        :param entity: object entity (class) to read
        :type entity: Base derived class
        :param predicate: List of logical criteria, e.g. (Event.date < a_date,
            Event.id > 10)
        :type predicate: list
        :param order_attr: Optional attribute to order objects by. Optional
            if the store has a read cache for the entity.
        :type order_attr: string
        :rtype: list

        """
        query = self._get_read_query(entity, predicate)

        # order_attr given in parameter list overrides any other order attribute
        if order_attr:
            query = query.order_by(None)
            query = query.order_by(order_attr)

        return query.all()

    def read(self, entity, index, predicate=None, order_attr=None):
        """
        Read and return the object at the given index from the list of objects
        that meet the predicate provided by the caller. The attribute provided
        in order_attr is used to determine the sort order.
        If the store has a sequential read cache for the entity (see
        init_sequential_read_cache() the order_attr will be determined from
        there.

        :param entity: Class of the object to read
        :param predicate: List of logical criteria, e.g. (Event.date < a_date,
            Event.id > 10)
        :type predicate: list
        :param order_attr: attribute that determines the sort order. Optional
            if the store has a read cache for the entity.
        :type order_attr: string
        :rtype: list

        """
        cache = self._read_caches[entity]
        if cache and not predicate:
            return cache[index]
        else:
            query = self._get_read_query(entity, predicate)

            # order_attr given in parameter list overrides any other order attr
            if order_attr:
                query = query.order_by(None)
                query = query.order_by(order_attr)
            return query[index]

    # Counting

    def count(self, entity, predicate=None):
        """
        Count and return the number of objects from the store that meet the
        predicate provided by the caller

        :param entity: object entity (class) to read
        :type entity: Base derived class
        :param predicate: List of logical criteria, e.g. (Event.date < a_date,
            Event.id > 10)
        :type predicate: list
        :rtype: integer

        """
        cache = self._read_caches[entity]
        if cache and not predicate:
            return len(cache)
        else:
            query = self._get_read_query(entity, predicate)
            return query.count()


    # Sequential Read Cache Management

    def init_sequential_read_cache(self, entity, order_attr):
        """
        Creates and subsequently manages a read cache for better performance
        during sequential access.

        :param entity: the class for the entity that should be cached
        :type entity: Base
        :order_attr: the class attribute that defines the order
        :type order_attr: string

        """
        cache = SequentialReadCache(self._session, entity, order_attr)
        self._read_caches[entity] = cache

    def refresh_cache(self, entity):
        """
        Refresh the sequential read cache for an entity.

        You normally don't call this manually.

        """
        cache = self._read_caches[entity]
        cache.refresh()

