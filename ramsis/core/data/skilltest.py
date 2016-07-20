# -*- encoding: utf-8 -*-
"""
Skill tests for forecasts
    
Copyright (C) 2015, SED (ETH Zurich)

"""

from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from ormbase import OrmBase


class SkillTest(OrmBase):

    # region ORM Declarations
    __tablename__ = 'skill_tests'
    id = Column(Integer, primary_key=True)
    skill_score = Column(Float)
    test_interval = Column(Float)
    spatial_extent = Column(Float)  # TODO: define
    # ModelResult relation
    model_result = relationship('ModelResult',
                                back_populates='skill_test',
                                uselist=False)
    # SnapshotCatalog relation
    reference_catalog_id = Column(Integer, ForeignKey('snapshot_catalogs.id'))
    reference_catalog = relationship('SnapshotCatalog',
                                     back_populates='skill_test',
                                     cascade='all')
    # endregion
