# -*- encoding: utf-8 -*-
# Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""
Injection well information

"""


from sqlalchemy import Column, Integer, Float
from ormbase import OrmBase


class InjectionWell(OrmBase):
    """
    Injection well information

    :ivar float well_tip_x: Well tip x coordinate [m]
    :ivar float well_tip_y: Well tip y coordinate [m]
    :ivar float well_tip_z: Well tip depth [m] (positive downwards)

    """

    # ORM declarations
    __tablename__ = 'injectionwell'
    id = Column(Integer, primary_key=True)
    well_tip_lat = Column(Float)
    well_tip_lon = Column(Float)
    well_tip_depth = Column(Float)

    # Data attributes (required for flattening)
    data_attrs = ['well_tip_z', 'well_tip_x', 'well_tip_y']

    def __init__(self, well_tip_z, well_tip_x, well_tip_y):
        """
        The initialisation parameters are the same as the member variables.
        See class description for details.

        """
        self.well_tip_x = well_tip_x
        self.well_tip_y = well_tip_y
        self.well_tip_z = well_tip_z
