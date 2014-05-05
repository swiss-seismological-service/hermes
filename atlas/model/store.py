# -*- encoding: utf-8 -*-
"""
Defines the Store class which writes and reads data from a sqlalchemy created
sqlite database.

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker


class SequentialReadCache:
    """
    Provides a read cache for improved performance during sequential access.

    The read cache uses a PageCache to fetch objects from the db page wise. This
    reduces db access during sequential access.
    It also manages a query for the entity that it manages and provides
    functions for container type access such as __len__() and __getitem__().

    """

    def __init__(self, session, entity, order_attr, size):
        self.entity = entity
        self.order_attr = order_attr
        self.session = session
        self.query = None
        self._num_events = 0
        self._page_size = size
        self._page_start = 0
        self._cached_results = None

        self.refresh()

    def refresh(self):
        self.query = self.session.query(self.entity).order_by(self.order_attr)
        self._num_events = self.query.count()

    def invalidate(self):
        self._page_start = 0
        self._num_events = 0
        self._cached_results = None

    def __len__(self):
        return self._num_events

    def __getitem__(self, index):
        """Returns the item at index from the cache

        If the item at index is outside the currently loaded page, the current
        page is swapped for the one containing index.

        """
        if self.query is None:
            return None

        # Translate python style relative index to absolute index
        if index < 0:
            index += self._num_events

        page_end = self._page_start + self._page_size
        page_offset = index % self._page_size

        if self._cached_results and index in range(self._page_start, page_end):
            return self._cached_results[page_offset]
        else:
            self._page_start = (index / self._page_size) * self._page_size
            page_end = self._page_start + self._page_size
            self._cached_results = self.query[self._page_start:page_end]
            return self._cached_results[page_offset]


class Store:
    """
    Manages access to the store (database)

    The store uses sqlalchemy to persist event objects to the
    database. As a consequence all objects that need to be persisted
    should inherit from the declarative base provided by :mod:`base`

    A store provides read caches for improved read performance. Caches must
    be created explicitly by calling init_read_cache(entity) where
    entity is the class for which reading should be cached.

    :ivar engine: sqlalchemy Engine that manages connections to the db

    """

    def __init__(self, store_url, model):
        """
        :param store_url: Database url
        :param model: sqlalchemy data model (declarative base)

        """
        self.engine = create_engine(store_url, echo=False)
        self.model = model
        self.model.metadata.create_all(self.engine, checkfirst=True)
        session = sessionmaker(bind=self.engine)
        self._read_caches = {}
        self.session = session()

    def purge(self, entity=None):
        """
        Deletes all data from the store

        If entity is given, only data for this entity will be deleted

        """
        if entity is not None:
            cache = self._read_caches.get(entity)
            if cache is not None:
                cache.invalidate()
            delete = entity.__table__.delete()
            self.engine.execute(delete)
        else:
            self.model.metadata.drop_all(bind=self.engine)
            self.model.metadata.create_all(self.engine)

    def commit(self):
        """
        Commits pending changes to the store immediately

        """
        self.session.commit()

    def close(self):
        self.session.close()
        self.session = None

    # Reading and Writing

    def add(self, objects):
        """
        Convenience method to add and commit new objects to the store. All
        objects must be of the same type (class).

        :param objects: A list of objects
        :type objects: List of model derived objects

        """
        self.session.add_all(objects)
        self.commit()

        # if we have a read cache for this class, we need to refresh it now
        cache = self._read_caches.get(objects[0].__class__)
        if cache is not None:
            cache.invalidate()
            cache.refresh()

    def _get_read_query(self, entity, predicate):
        """
        # get the query from the sequential read cache if we have one for
        # this entity. otherwise create a new query.
        cache = self._read_caches.get(entity)
        query = None
        if cache is not None:
            query = cache.query
        else:
            query = self.session.query(entity)
        """
        query = self.session.query(entity)
        if predicate is not None:
            query = query.filter(predicate)

        return query

    def read_first(self, entity, predicate=None, order=None):
        """
        Read and return the first object from the store that meets the
        predicate provided by the caller. The attribute provided in order
        is used to determine the sort order.
        If the store has a sequential read cache for the entity (see
        init_sequential_read_cache() the order will be determined from
        there.

        :param entity: Class of the object to read
        :param predicate: sqlalchemy filter predicate
        :type predicate: sqlalchemy filter predicate
        :param order: attribute that determines the sort order. Optional
            if the store has a read cache for the entity.
        :type order: string
        :rtype: list

        """
        query = self._get_read_query(entity, predicate)

        # order given in parameter list overrides any other order attribute
        if order is not None:
            query = query.order_by(None)
            query = query.order_by(order)

        return query.first()

    def read_last(self, entity, predicate=None, order=None):
        """
        Read and return the last object from the store that meets the
        predicate provided by the caller. The attribute provided in order
        is used to determine the sort order.
        If the store has a sequential read cache for the entity (see
        init_sequential_read_cache() the order will be determined from
        there.

        :param entity: Class of the object to read
        :param predicate: sqlalchemy filter predicate
        :type predicate: sqlalchemy filter predicate
        :param order: attribute that determines the sort order. Optional
            if the store has a read cache for the entity.
        :type order: string
        :rtype: list

        """
        query = self._get_read_query(entity, predicate)

        cache = self._read_caches.get(entity)
        if cache is not None:
            order = order if order else cache.order_attr

        # revert order
        query = query.order_by(None)
        query = query.order_by(desc(order))

        return query.first()

    def read_all(self, entity, predicate=None, order=None):
        """
        Read and return all objects from the store that meet the predicate
        provided by the caller

        :param entity: object entity (class) to read
        :type entity: model derived class
        :param predicate: sqlalchemy filter predicate
        :type predicate: sqlalchemy filter predicate
        :param order: Attribute to order objects by. Optional
            if the store has a read cache for the entity.
        :type order: string
        :rtype: list

        """
        query = self._get_read_query(entity, predicate)

        # order given in parameter list overrides any other order attribute
        if order is not None:
            query = query.order_by(None)
            query = query.order_by(order)

        return query.all()

    def read(self, entity, index, predicate=None, order=None):
        """
        Read and return the object at the given index from the list of objects
        that meet the predicate provided by the caller. The attribute provided
        in order is used to determine the sort order.
        If the store has a sequential read cache for the entity (see
        init_sequential_read_cache() the order will be determined from
        there.

        :param entity: Class of the object to read
        :param predicate: sqlalchemy filter predicate
        :type predicate: sqlalchemy filter predicate
        :param order: attribute that determines the sort order. Optional
            if the store has a read cache for the entity.
        :type order: string
        :rtype: list

        """
        cache = self._read_caches.get(entity)
        if cache is not None and predicate is None:
            return cache[index]
        else:
            query = self._get_read_query(entity, predicate)

            # order given in parameter list overrides any other order attr
            if order:
                query = query.order_by(None)
                query = query.order_by(order)
            return query[index]

    # Counting

    def count(self, entity, predicate=None):
        """
        Count and return the number of objects from the store that meet the
        predicate provided by the caller

        :param entity: object entity (class) to read
        :type entity: model derived class
        :param predicate: sqlalchemy filter predicate
        :type predicate: sqlalchemy filter predicate
        :rtype: integer

        """
        cache = self._read_caches.get(entity)
        if cache is not None and predicate is None:
            return len(cache)
        else:
            query = self._get_read_query(entity, predicate)
            return query.count()

    # Sequential Read Cache Management

    def init_sequential_read_cache(self, entity, order, size=10000):
        """
        Creates and subsequently manages a read cache for better performance
        during sequential access.

        :param entity: the class for the entity that should be cached
        :type entity: datamodel
        :order: the class attribute that defines the order
        :type order: string

        """
        cache = SequentialReadCache(self.session, entity, order, size)
        self._read_caches[entity] = cache

    def refresh_cache(self, entity):
        """
        Refresh the sequential read cache for an entity.

        You normally don't call this manually.

        """
        cache = self._read_caches.get(entity)
        cache.refresh()