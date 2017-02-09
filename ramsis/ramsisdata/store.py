# -*- encoding: utf-8 -*-
"""
The Store manages everything related to sqlalchemy

Copyright (C) 2013-2017, ETH Zurich - Swiss Seismological Service SED

"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


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

    def __init__(self, store_url, model):
        """
        :param store_url: Database url
        :param model: sqlalchemy data data (declarative base)

        """
        self.engine = create_engine(store_url)
        self.model = model
        self.model.metadata.create_all(self.engine, checkfirst=True)
        session = sessionmaker(bind=self.engine)
        self.session = session()

    def commit(self):
        self.session.commit()

    def close(self):
        self.session.close()
        self.session = None

