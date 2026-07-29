import math

TILE_SIZE = 256
MAX_LATITUDE = 85.05112878


def clamp_latitude(latitude):
    return max(-MAX_LATITUDE, min(MAX_LATITUDE, latitude))


def latlon_to_world(latitude, longitude, zoom):
    latitude = clamp_latitude(float(latitude))
    longitude = float(longitude)
    scale = TILE_SIZE * (1 << zoom)
    x = (longitude + 180.0) / 360.0 * scale
    sin_lat = math.sin(math.radians(latitude))
    y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * scale
    return x, y


def world_to_latlon(x, y, zoom):
    scale = TILE_SIZE * (1 << zoom)
    longitude = x / scale * 360.0 - 180.0
    n = math.pi - 2.0 * math.pi * y / scale
    latitude = math.degrees(math.atan(math.sinh(n)))
    return latitude, longitude
