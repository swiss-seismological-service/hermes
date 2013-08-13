# -*- encoding: utf-8 -*-
"""
Data storage tools

Some helper classes for SQLAlchemy
    
"""


class PageCache(object):
    """A page cache for sqlalchemy queries

    The page cache, when accessed through the index operator [],
    loads one page of results at the time. This improves performance
    for sequential access while at the same time keeping the memory
    foot-print low.

    """

    def __init__(self, query=None, page_size=100):
        """
        :param query: the sqlalchemy query that loads the results from the db
        :type query: sqlalchemy query
        :param page_size: number of results to load per page
        :type page_size: int

        """
        self._query = query
        self._page_size = page_size
        self._page_start = 0
        self._cached_results = None

    @property
    def query(self):
        return self._query

    @query.setter
    def query(self, value):
        """Setting an new query automatically invalidates the cache"""
        self._query = value
        self.invalidate()

    def invalidate(self):
        """Invalidates the cache

        Causes the results to be reloaded on the next access

        """
        self._page_start = 0
        self._cached_results = None

    def __getitem__(self, index):
        """Returns the item at index from the cache

        If the item at index is outside the currently loaded page, the current
        page is swapped for the one containing index.

        """
        if self._query is None:
            return None

        page_end = self._page_start + self._page_size
        page_offset = index % self._page_size

        if self._cached_results and index in range(self._page_start, page_end):
            return self._cached_results[page_offset]
        else:
            self._page_start = (index / self._page_size) * self._page_size
            page_end = self._page_start + self._page_size
            self._cached_results = self.query[self._page_start:page_end]
            return self._cached_results[page_offset]