# -*- encoding: utf-8 -*-
# Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED
"""
Basic 3D geometric objects and functions

"""

from collections import namedtuple

class Point:
    """
    A point in 3D space defined by coordinates x, y and z where z

    """
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def in_cube(self, cube):
        """
        Returns true if a point is within a cube

        :param cube: cube defining boundaries for points
        :return: true if point is in cube

        """
        xmin = cube.origin.x
        xmax = xmin + cube.size
        ymin = cube.origin.y
        ymax = ymin + cube.size
        zmin = cube.origin.z
        zmax = zmin + cube.size
        return (xmin <= self.x < xmax and
                ymin <= self.y < ymax and
                zmin <= self.z < zmax)


Cube = namedtuple('Cube', 'origin size')
"""
A cube defined by an origin (point) and a side length (size)

"""
