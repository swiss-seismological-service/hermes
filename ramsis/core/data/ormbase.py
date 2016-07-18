# -*- encoding: utf-8 -*-
"""
Provides the declarative base for all persistent data objects

Objects which should be persisted through sqlalchemy must inherit from
the ``OrmBase`` class defined in this module.
``OrmBase`` derived classes are required to provide a class variable data_attrs
that specifies all the attributes which contain actual domain relevant data.
This attribute is used to flatten the content when passing data to matlab.

"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from PyQt4.QtCore import QObject, pyqtSignal, pyqtWrapperType

# Base class for objects that are to be persisted by sqlalchemy
OrmBase = declarative_base()


class DeclarativeQObjectMeta(pyqtWrapperType, DeclarativeMeta):
    """
    Metaclass that allows us to inherit from both QObject and OrmBase

    """
    def __init__(cls, name, bases, dct):
        pyqtWrapperType.__init__(cls, name, bases, dct)
        DeclarativeMeta.__init__(cls, name, bases, dct)
