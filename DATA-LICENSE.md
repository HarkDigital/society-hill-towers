# Data and font licenses

Philly3D's code is MIT (see `LICENSE`). The data the page embeds comes from several open
sources under their own terms. This file is a factual inventory of what came from where,
which scripts made each file, and what each source's license asks. It is not legal advice.

## OpenStreetMap (ODbL 1.0)

The following files in `3d-model/` are derivative databases of OpenStreetMap data,
© OpenStreetMap contributors, made available under the Open Database License 1.0
(https://opendatacommons.org/licenses/odbl/1-0/):

| File | Made by | From |
|---|---|---|
| `scene.json`, `scene_wide.json`, `scene_south.json` | `process_osm.py` (heights patched by `lidar_core.py` / `lidar_join.py`, attributes by `patch_scenes_facade.py`) | the raw Overpass dumps `osm_raw.json` / `osm_wide_raw.json` / `osm_south_raw.json` (not committed) |
| `parts_wide.json` | `process_osm.py` | OSM `building:part` ways in the wide dump |
| `wide.b64` | `pack_wide.py` | `scene_wide.json` + `scene_south.json` + `parts_wide.json` |
| `city.b64` | `pack_city.py` | `osm_city_raw.json` (not committed; fetched by `fetch_city.py`) |
| `street_labels.json`, `street_sdf.json` | `bake_street_labels.py`, `bake_street_sdf.py` | street names and geometry in the three scene files |
| `overpasses.json` | `bake_overpasses.py` | bridge / tunnel / layer tags and geometry in the raw dumps |
| `traffic.b64` (in part) | `bake_traffic.py` | OSM drivable-way geometry, oneway and tunnel tags; the traffic volumes themselves are PennDOT data (below) |
| `wwb.json` | `fetch_south.py` | the Walt Whitman Bridge motorway alignment |
| `wide_names.json` | hand-compiled from OSM names and tags plus `wide_landmarks_research.json` | OSM landmark names |
| `nw_water.json` | `fetch_nw_water.py` | Overpass water polygons over the NW hills box |
| `report_wide.json`, `report_south.json` | `process_osm.py` | summary statistics of the extracts |

`lidar_city_heights.json` is keyed by OSM way id; its height values are City of
Philadelphia data (below). The raw Overpass dumps and `city_tiles/` are OSM data too.

What ODbL asks: attribution wherever the data or works made from it are published, and
share-alike (the same license) for any derivative *database* that is publicly used. The
rendered page is a Produced Work under the license and carries the notice: the bottom
credit line (`#osmcredit`) and the About panel link to
https://www.openstreetmap.org/copyright. That link must stay in any copy of the page, and
the files above must keep this notice if they are redistributed.

## City of Philadelphia open data (CC-BY 4.0 unless the dataset says otherwise)

| File | Made by | Source |
|---|---|---|
| `places.json` | `fetch_places.py` → `bake_places.py` | Philadelphia Register historic districts and neighborhood boundaries, City of Philadelphia via OpenDataPhilly / phl.carto.com. CC-BY 4.0: attribution to the City of Philadelphia is required. |
| `trees.b64`, `tree_names.json` | `fetch_trees.py` → `pack_trees.py` | Philadelphia Parks & Recreation Tree Inventory 2025 (OpenDataPhilly / City ArcGIS) |
| `poles.b64` | `fetch_poles.py` → `pack_poles.py` | Streets Department Street Poles inventory (OpenDataPhilly / City ArcGIS, 203,058 poles) |
| `nw_parks.json` | `fetch_nw_parks.py` | Parks & Recreation `PPR_Properties` parkland boundaries (OpenDataPhilly) |
| building heights: `lidar_city_heights.json`, the `h` / `roof` values in the scene files, `lidar_report.json` | `fetch_footprints.py` → `lidar_join.py`; `lidar_core.py` | `LI_BUILDING_FOOTPRINTS` (Licenses & Inspections / OIT) with 2022-LiDAR-derived maximum heights; the 2022 QL1 LiDAR point cloud of the City's survey (NOAA Digital Coast COPC tiles, cached in `lidar_cache/`, not committed) for the core roof forms |
| facade attributes: the `fa` values in the scene files and the packed `attr` word in `wide.b64` / `city.b64` | `fetch_opa.py` → `opa_join.py` → `patch_scenes_facade.py` | Office of Property Assessment property records (phl.carto.com) |
| roof colours: `facade_palette.json` and the `rp` / roof indices | `roof_colors.py` → `patch_scenes_facade.py` | `CityImagery_2024_3in` orthophoto tiles (City of Philadelphia ArcGIS Online) |

City datasets on OpenDataPhilly are generally released under CC-BY 4.0
(https://creativecommons.org/licenses/by/4.0/); attribution ("City of Philadelphia" and the
department named above) is required; the page's credit line carries it on screens wider than 900 px, and the Credits link (the About panel) carries it on every screen. Check the
individual dataset page on OpenDataPhilly for any exception before reusing a file.

## USGS (public domain)

`dem.json`, `dem_wide.json`, `dem_south.json`, `dem_city.json`, `dem_nw.json` (written by
`fetch_wide.py`, `fetch_south.py`, `fetch_city.py`, `fetch_dem_nw.py`) are resampled from
the USGS National Elevation Dataset / 3DEP 10 m grid. USGS elevation data is a work of the
United States government and in the public domain.

## PennDOT (open data)

The traffic volumes in `traffic.b64` (`fetch_traffic.py` → `bake_traffic.py`) are annual
average daily traffic counts from PennDOT's Roadway Management System (RMSTRAFFIC), published
as open data on the Pennsylvania open-data portal. Attribution to PennDOT is carried in the
credit line.

## Live feeds (fetched by the page, not embedded)

SEPTA TransitView (SEPTA's public API; SEPTA marks belong to SEPTA and the page carries a
non-affiliation notice), Indego station status (Bicycle Transit Systems), adsb.fi community
ADS-B data through the philly3d.com `/adsb` proxy, aisstream.io AIS positions, Open-Meteo
(CC-BY 4.0), and OpenStreetMap Nominatim for search (ODbL data; subject to the Nominatim
usage policy). Each feed has its own terms of use; the page credits them.

## Fonts (SIL Open Font License 1.1)

Montserrat (Julieta Ulanovsky and contributors) is used for all type: the embedded woff2
faces in `3d-model/style.css`, `3d-model/brand/Montserrat-SemiBold.ttf` (the wordmark) and
`3d-model/MontserratItalic.ttf` (the street-name SDF atlas). The license text is at
`3d-model/brand/OFL.txt`. The OFL permits embedding and redistribution; the font may not be
sold on its own and any modified version must carry a different name.

## Research and hand-written files

`meta.json`, `realism_research.json`, `headhouse_blocks_research.json`,
`fenestration_research.json`, `wide_landmarks_research.json`, `south_geometry_research.json`
and `geo_audit.json` are notes compiled from public sources (photographs, CTBUH, DRPA, OPA,
city LiDAR, OSM tags). They are covered by the repository's MIT license; facts drawn from
OSM or City data remain subject to the terms above.

## Three.js

`3d-model/three.min.js` is Three.js r149, MIT License, © 2010–2023 three.js authors.
