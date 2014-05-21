# -*- encoding: utf-8 -*-
"""
Provides the declarative base for all persistent domainmodel objects

Objects which should be persisted through sqlalchemy must inherit from
the **DataModel** class defined in this module.
DataModel derived classes are required to provide a class variable data_attrs
that specifies all the attributes which contain actual domain relevant data.
This attribute is used to flatten the content when passing data to matlab.

"""

from sqlalchemy.ext.declarative import declarative_base

# Base class for objects that are to be persisted by sqlalchemy
DataModel = declarative_base()