# Copyright 2019, ETH Zurich - Swiss Seismological Service SED
"""
General purpose IO utilities.
"""

import abc

from ramsis.utils.error import Error


class IOError(Error):
    """Base IO error ({})."""


class IOBase(abc.ABC):
    """
    Abstract IO base class
    """

    @abc.abstractmethod
    def __iter__(self):
        while False:
            yield None
