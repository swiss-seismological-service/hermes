# -*- encoding: utf-8 -*-
"""
Provides the declarative base for all persistent model objects

Objects which should be persisted through sqlalchemy must inherit from
the **DataModel** class defined in this module.

"""

from sqlalchemy.ext.declarative import declarative_base

# Base class for objects that are to be persisted by sqlalchemy
DataModel = declarative_base()