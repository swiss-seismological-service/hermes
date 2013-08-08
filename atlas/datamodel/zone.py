# Atlas
# Copyright (C) 2013 Lukas Heiniger

class Location(object):
    """
    Represents a geographic zone (e.g. a municipality)

    """

    def __init__(self, name, location, inventory = None):
        # TODO: add range check
        self.name = name
        self.location = location
        if inventory is None:
            self.inventory = []
