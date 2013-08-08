# Atlas
# Copyright (C) 2013 Lukas Heiniger

class ZoneInventoryItem(object):
    """
    Contains the percentage of one specific building class within the zone it belongs to.

    """

    def __init__(self, percentage, building_class, insured_value):
        # TODO: add range check
        self.percentage = percentage
        self.building_class = building_class
        self.insured_value = insured_value