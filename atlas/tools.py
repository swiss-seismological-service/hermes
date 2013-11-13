# -*- encoding: utf-8 -*-
"""
A bunch of useful general helpers
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import functools


# note that this decorator ignores **kwargs
def memoize(obj):
    """
    Memoization decorator

    A memoize decorated function is only evaluated on the first call. The result
    is cached and returned without reevaluation on subsequent calls.
    (from https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize)

    """
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        if args not in cache:
            cache[args] = obj(*args, **kwargs)
        return cache[args]
    return memoizer