# -*- encoding: utf-8 -*-
"""
Provides the declarative base for all persistent data objects

Objects which should be persisted through sqlalchemy must inherit from
the ``OrmBase`` class defined in this module.

"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TypeDecorator, VARCHAR
import json

# Base class for objects that are to be persisted by sqlalchemy
OrmBase = declarative_base()


class JSONEncodedDict(TypeDecorator):
    "Represents an immutable structure as a json-encoded string."

    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value
