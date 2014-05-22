# -*- encoding: utf-8 -*-
"""
Injection well information

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""


from sqlalchemy import Column, Integer, Float, DateTime
from datamodel import DataModel



class InjectionWell(DataModel):
    """
    Injection well information

    :ivar well_tip_lat: Well tip latitude
    :type well_tip_latitude: float
    :ivar well_tip_longitude: well tip longitude
    :type well_tip_longitude: float
    :ivar well_tip_depth: well tip depth [m] (positive downwards)
    :type well_tip_depth: float

    """

    # ORM declarations
    __tablename__ = 'injectionwell'
    id = Column(Integer, primary_key=True)
    well_tip_lat = Column(Float)
    well_tip_lon = Column(Float)
    well_tip_depth = Column(Float)

    # Data attributes (required for flattening)
    data_attrs = ['well_tip_depth', 'well_tip_latitude', 'well_tip_longitude']

    def __init__(self, well_tip_depth, well_tip_lat, well_tip_lon):
        """
        The initialisation parameters are the same as the member variables.
        See class description for details.

        """
        self.well_tip_lat = well_tip_lat
        self.well_tip_lon = well_tip_lon
        self.well_tip_depth = well_tip_depth