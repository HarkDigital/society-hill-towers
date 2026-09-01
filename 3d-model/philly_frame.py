#!/usr/bin/env python3
"""The ONE local frame of the Philly3D model: lat/lon <-> scene metres.

Frame (identical to process_osm.py, which defines the scene, and to app.js,
which renders it):
  origin  = the area-weighted centroid of the three Society Hill Towers
            footprints (process_osm.py computes it from the OSM rings; the
            value below is what it wrote into scene.json's "origin")
  x       = east, metres   : (lon - LON0) * KX,  KX = 111320 * cos(LAT0)
  z       = south, metres  : (LAT0 - lat) * KZ,  KZ = 110574
  y       = up (not handled here)
Equirectangular, so it is only exact at the origin; over the 16 x 30 km far
ring the shear/scale error is well under a metre, which is why every tier
shares it unchanged.

History: a second family of scripts (the LiDAR/OPA joins, the pole/tree/place
packs, the NW patch fetches, pack_city/pack_wide's inline node projections)
hardcoded KX = 85350.0 with a 6-decimal origin. 85350 vs 85344.125 is a
6.9e-5 scale error, i.e. up to ~1.1 m of eastward drift at the far ring's
16.5 km edge (plus ~4 cm from the rounded origin) between the joined data
and the scene it was joined to. They now import this module instead; their
committed outputs still carry the old frame until each script is rerun.

process_osm.py rounds its own to_xz() to centimetres; this one does not, so
callers that need parity with scene.json coordinates round themselves.
"""
import math

LAT0 = 39.945473644755005     # scene.json "origin".lat (towers' centroid)
LON0 = -75.14474803850973     # scene.json "origin".lon
KX = 111320 * math.cos(math.radians(LAT0))   # metres per degree of longitude here (85344.125...)
KZ = 110574                                   # metres per degree of latitude


def to_xz(lat, lon):
    """(lat, lon) degrees -> (x east, z south) metres in the scene frame."""
    return (lon - LON0) * KX, (LAT0 - lat) * KZ


def to_latlon(x, z):
    """(x east, z south) metres in the scene frame -> (lat, lon) degrees."""
    return LAT0 - z / KZ, LON0 + x / KX


if __name__ == '__main__':
    # self-check: the frame is a pure affine map, so the round trip is exact to fp noise
    lat, lon = to_latlon(*to_xz(40.0, -75.2))
    assert abs(lat - 40.0) < 1e-12 and abs(lon + 75.2) < 1e-12, (lat, lon)
    print(f'LAT0={LAT0} LON0={LON0} KX={KX!r} KZ={KZ}')
    print(f'far-ring drift of the old KX=85350 frame at x=16500 m: {16500 * (85350.0 / KX - 1):.3f} m')
