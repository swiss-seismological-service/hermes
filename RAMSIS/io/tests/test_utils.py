import unittest

from RAMSIS.io.utils import RamsisCoordinateTransformer, IOBase

WGS84_PROJ = "epsg:4326"
UTM_PROJ = "+proj=utm +zone=32N +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
# These coordinates are equal (lat lon in wgs84, e,n in utm.)
LON = 7.0
LAT = 51.0

# 5595938.843164114 1019789.7913273775
EASTING = 349666.70366168075
NORTHING = 5631728.68267166
# Depth doesnt get reprojected, expect it to stay the same.
DEPTH = 0.0

# reference point in UTM coordinates, center of local
# coordinate reference system
REF_EASTING = 10000
REF_NORTHING = 20000


class TransformationCoordsTestCase(unittest.TestCase):
    """
    Test case for checking back and forth transformation
    between source proj and local coordinate system.
    """

    def test_multiple_conversions(self):
        transformer = RamsisCoordinateTransformer(REF_EASTING, REF_NORTHING,
                                                  UTM_PROJ, WGS84_PROJ)
        lat = LAT
        lon = LON
        easting = EASTING
        northing = NORTHING
        depth = DEPTH
        for i in range(10):
            easting, northing, depth = transformer.\
                pyproj_transform_to_local_coords(
                    lat, lon, depth)
            lat, lon, depth = transformer.pyproj_transform_from_local_coords(
                easting, northing, depth)
        self.assertAlmostEqual(lat, LAT)
        self.assertAlmostEqual(lon, LON)
        self.assertAlmostEqual(easting, EASTING)
        self.assertAlmostEqual(northing, NORTHING)
        self.assertAlmostEqual(depth, DEPTH)

    def test_iobase(self):
        iobase_to_local = IOBase(
            ref_easting=REF_EASTING, ref_northing=REF_NORTHING,
            ramsis_proj=UTM_PROJ, external_proj=WGS84_PROJ,
            transform_func_name='pyproj_transform_to_local_coords')
        iobase_to_external = IOBase(
            ref_easting=REF_EASTING, ref_northing=REF_NORTHING,
            ramsis_proj=UTM_PROJ, external_proj=WGS84_PROJ,
            transform_func_name='pyproj_transform_from_local_coords')

        easting, northing, depth = iobase_to_local.transform_func(
            LAT, LON, DEPTH)
        lat, lon, depth = iobase_to_external.transform_func(
            EASTING, NORTHING, depth)
        self.assertAlmostEqual(lat, LAT)
        self.assertAlmostEqual(lon, LON)
        self.assertAlmostEqual(easting, EASTING)
        self.assertAlmostEqual(northing, NORTHING)
