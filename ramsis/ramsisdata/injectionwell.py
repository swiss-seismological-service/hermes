# -*- encoding: utf-8 -*-
# Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""
Injection well information

"""


from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .ormbase import OrmBase


class InjectionWell(OrmBase):
    """
    Injection well information

    :ivar float well_tip_x: Well tip x coordinate [m]
    :ivar float well_tip_y: Well tip y coordinate [m]
    :ivar float well_tip_z: Well tip depth [m] (positive downwards)

    """

    # region ORM declarations
    __tablename__ = 'injection_wells'
    id = Column(Integer, primary_key=True)
    # Project relation
    project_id = Column(Integer, ForeignKey('projects.id'))
    project = relationship('Project', back_populates='injection_well')
    # WellSection relation
    sections = relationship('WellSection', back_populates='injection_well',
                            cascade='all, delete-orphan')
    # endregion

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

    @property
    def injection_point(self):
        # TODO: implement
        return (4740.3, 270645.0, 611631.0)


class WellSection(OrmBase):

    # region ORM Declarations
    __tablename__ = 'well_sections'
    id = Column(Integer, primary_key=True)
    cased = Column(Boolean)
    # TODO: add position
    # InjectionWell relation
    injection_well_id = Column(Integer, ForeignKey('injection_wells.id'))
    injection_well = relationship('InjectionWell', back_populates='sections')
    # endregion
