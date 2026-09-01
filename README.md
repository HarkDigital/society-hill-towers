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
- **Layers** (F): live SEPTA vehicles, Indego bike share, flights, ships, typical
  traffic, streetlights, street names, landmark labels, and neighborhood names.

## Build

No toolchain, plain Python 3 assembles the page:

```bash
cd 3d-model && python3 build.py
```

Open `3d-model/society-hill-towers.html` in any WebGL browser (or serve the folder with
`python3 -m http.server 8917`). Everything (Three.js, data, styles, fonts, icons) is
inlined into that one file: 22.83 MB raw, 9.77 MB gzipped as served. `build.py` prints a
size table per embedded blob and refuses to ship a missing input, a leftover placeholder,
or a page over 25 MB.

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
  Department Street Poles inventory; parkland: Parks & Recreation; neighborhoods and
  historic districts: City of Philadelphia via OpenDataPhilly (CC-BY); traffic volumes:
  PennDOT RMSTRAFFIC.
- Live: SEPTA TransitView, Indego / Bicycle Transit Systems, adsb.fi (ADS-B), aisstream.io
  (AIS), Open-Meteo (weather), OpenStreetMap Nominatim (search).
- Rendering: [Three.js](https://threejs.org/) r149 (MIT), inlined.
- Landmark massing and colors researched from public photographs, Philadelphia OPA
  parcels, and city LiDAR.

## License

- Code: MIT, © 2026 Mike Harkins / Hark Digital (see `LICENSE`).
- Data: OpenStreetMap under ODbL 1.0; City of Philadelphia open data under CC-BY 4.0 and
  the other sources' open terms; see `DATA-LICENSE.md`.
- Type: Montserrat, SIL Open Font License 1.1 (`3d-model/brand/OFL.txt`).
