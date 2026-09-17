<p align="center"><img src="3d-model/brand/dist/lockup.png" alt="Philly3D" width="440"></p>

A living, single-file 3D model of Philadelphia: every block of the city at its true
measured height, from the detailed Society Hill core (including Society Hill Towers,
I.M. Pei, 1964) out to the full city fabric, with real terrain, the Delaware
waterfront, the bridges, live SEPTA vehicles, flights and ships, live weather, and a
real solar clock over it all.

**Live model:** https://philly3d.com/
(fallback copy: https://harkdigital.github.io/society-hill-towers/)

- **Fly.** Drag, scroll, or press W A S D; E/Q for altitude, shift to boost, scroll
  sets cruise speed. Any first touch takes off.
- **Sun and sky** (T): any date and time of day with real Philadelphia solar
  geometry, dusk and night with lit windows, and the real moon.
- **Weather.** Live conditions from Open-Meteo: rain, snow, fog and lightning as they
  happen, snow settling on roofs and lawns, wet streets. `?wx=storm` (or clear,
  overcast, fog, drizzle, rain, downpour, hail, snow, blizzard, sleet) pins a preset.
  The haze follows the city's own air monitors: a smoke day shortens the view and tints
  the sky tan (`?aqi=unhealthy` pins it).
- **Layers** (F): live SEPTA vehicles, Indego bike share, flights, ships, Amtrak trains
  riding the real Northeast Corridor and Keystone tracks, concerts, typical traffic, live
  street closures (barrels and cones from the Streets Department's permits, fresh asphalt on
  the season's paved blocks), historical markers, public art, streetlights, street names,
  landmark labels, and neighborhood names.
- **Markets.** The city's 34 farmers' markets pitch their tents only while the clock
  says they are open; tap a tent for the hours and payments, or search a market by name.
- **Markers and art.** The state's 348 historical markers stand at their posts with the
  full text a tap away, and the city's Percent for Art works on their plinths.
- **Close by.** Everything that stands on the ground (vehicles, docks, trains, markers, art,
  closures, tents) draws only within half a mile of you, each closed block, marker and
  artwork under its own pin; flights and ships stay visible across the city.
- **Lights.** After dark the researched crowns, City Hall's tower and the Ben Franklin Bridge
  glow in the night's colour: a Philadelphia team's on its game day (Eagles, then Phillies,
  Flyers, Sixers), otherwise the cause on BOMA Philadelphia's Building Illumination Calendar,
  else white. The time panel names it; `?lights=eagles` or `?lights=purple` pins it.
- **Search** (/): an address, a landmark, a neighborhood, a street, a SEPTA route, and
  near six thousand named places from the city's own basemap: schools, churches, parks,
  rec centers, hospitals, libraries.

## Build

No toolchain, plain Python 3 assembles the page:

```bash
cd 3d-model && python3 build.py
```

Open `3d-model/society-hill-towers.html` in any WebGL browser (or serve the folder with
`python3 -m http.server 8917`). Everything (Three.js, data, styles, fonts, icons) is
inlined into that one file: 25.31 MB raw, 10.73 MB gzipped as served. `build.py` prints a
size table per embedded blob and refuses to ship a missing input, a leftover placeholder,
or a page over 75 MB.

The data pipeline (fetch, process, pack, bake) is Python too. Its scripts need a venv:

```bash
cd 3d-model
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # shapely, numpy, pyproj, laspy[lazrs], Pillow
python3 pipeline.py --graph              # the pipeline as a dependency graph
python3 -m unittest discover -s tests    # the test suite
python3 docs_check.py                    # handoff.md documents every input and script
```

See `handoff.md` for the file table, architecture and hard-won gotchas, `devlog.md` for
the round-by-round development log, and `CLAUDE.md` for the agent-facing summary. Brand
assets live in `3d-model/brand/`; `make_brand.py` regenerates `brand/dist/`.

## Data & credits

- Building footprints, roads, land use, bridges and street names ©
  [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, ODbL.
- Elevation from the USGS National Elevation Dataset (10 m).
- Building heights from the City of Philadelphia 2022 LiDAR survey (building footprints
  layer and point cloud); facade era, material and use from OPA property records; roof
  colours sampled from the City's 2024 orthophotos.
- Street trees: Philadelphia Parks & Recreation Tree Inventory 2025; streetlights: Streets
  Department Street Poles inventory; parkland: Parks & Recreation; neighborhoods, historic
  districts, farmers' markets, Percent for Art and the named places of the city basemap: City
  of Philadelphia via OpenDataPhilly (CC-BY); historical markers: Pennsylvania Historical and Museum Commission (public
  domain); traffic volumes: PennDOT RMSTRAFFIC.
- Live: SEPTA TransitView, Indego / Bicycle Transit Systems, adsb.fi (ADS-B), aisstream.io
  (AIS), Amtraker (Amtrak positions, ODC-By), Open-Meteo (weather), Air Management
  Services (air quality), the Streets Department (closures), ESPN's public scoreboards (scores
  and the game days that colour the skyline), BOMA Philadelphia's Building Illumination
  Calendar (the other nights' colours), OpenStreetMap Nominatim (search).
- Rendering: [Three.js](https://threejs.org/) r149 (MIT), inlined.
- Landmark massing and colors researched from public photographs, Philadelphia OPA
  parcels, and city LiDAR.

## License

- Code: MIT, © 2026 Mike Harkins / Hark Digital (see `LICENSE`).
- Data: OpenStreetMap under ODbL 1.0; City of Philadelphia open data under CC-BY 4.0 and
  the other sources' open terms; see `DATA-LICENSE.md`.
- Type: Montserrat, SIL Open Font License 1.1 (`3d-model/brand/OFL.txt`).
