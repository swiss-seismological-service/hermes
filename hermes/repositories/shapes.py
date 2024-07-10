from geoalchemy2 import WKBElement
from geoalchemy2.shape import to_shape

# Type and conversion function for the DB model's polygon field
PolygonType = WKBElement
polygon_converter = to_shape
