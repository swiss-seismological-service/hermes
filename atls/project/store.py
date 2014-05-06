# -*- encoding: utf-8 -*-
"""
Defines the Store class which writes and reads data from a sqlalchemy created
sqlite database.

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
import time


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
        :param model: sqlalchemy data domainmodel (declarative base)

        """
        self.engine = create_engine(store_url, echo=False)
        self.model = model
        self.model.metadata.create_all(self.engine, checkfirst=True)
        session = sessionmaker(bind=self.engine)
        self.session = session()

    def purge(self, entity=None):
        """
        Deletes all data from the store

        If entity is given, only data for this entity will be deleted

        """
        if entity is not None:
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
        :type objects: List of domainmodel derived objects

        """
        self.session.add_all(objects)
        self.commit()

    def _new_read_query(self, entity, predicate):
        """
        Create and return a read query for the entity *entity* with the optional
        predicate given in *predicate*.

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

        :param entity: Class of the object to read
        :param predicate: sqlalchemy filter predicate
        :type predicate: sqlalchemy filter predicate
        :param order: attribute that determines the sort order. Optional
            if the store has a read cache for the entity.
        :type order: string
        :rtype: list

        """
        query = self._new_read_query(entity, predicate)
        # order given in parameter list overrides any other order attribute
        if order is not None:
            query = query.order_by(order)
        return query.first()

    def read_last(self, entity, predicate=None, order=None):
        """
        Read and return the last object from the store that meets the
        predicate provided by the caller. The attribute provided in order
        is used to determine the sort order.

        :param entity: Class of the object to read
        :param predicate: sqlalchemy filter predicate
        :type predicate: sqlalchemy filter predicate
        :param order: attribute that determines the sort order. Optional
            if the store has a read cache for the entity.
        :type order: string
        :rtype: list

        """
        query = self._new_read_query(entity, predicate)
        # revert order
        query = query.order_by(None)
        query = query.order_by(desc(order))
        return query.first()

    def read_all(self, entity, predicate=None, order=None):
        """
        Read and return all objects from the store that meet the predicate
        provided by the caller

        :param entity: object entity (class) to read
        :type entity: domainmodel derived class
        :param predicate: sqlalchemy filter predicate
        :type predicate: sqlalchemy filter predicate
        :param order: Attribute to order objects by
        :type order: string
        :rtype: list

        """
        query = self._new_read_query(entity, predicate)
        # order given in parameter list overrides any other order attribute
        if order is not None:
            query = query.order_by(None)
            query = query.order_by(order)
        t0 = time.clock()
        results = query.all()
        tr = time.clock() - t0
        print 'read all finished with after {} seconds'.format(tr)
        return results

    def read(self, entity, index, predicate=None, order=None):
        """
        Read and return the object at the given index from the list of objects
        that meet the predicate provided by the caller. The attribute provided
        in order is used to determine the sort order.

        :param entity: Class of the object to read
        :param predicate: sqlalchemy filter predicate
        :type predicate: sqlalchemy filter predicate
        :param order: attribute that determines the sort order
        :type order: string
        :rtype: list

        """
        query = self._new_read_query(entity, predicate)
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
        :type entity: domainmodel derived class
        :param predicate: sqlalchemy filter predicate
        :type predicate: sqlalchemy filter predicate
        :rtype: integer

        """
        query = self._new_read_query(entity, predicate)
        return query.count()