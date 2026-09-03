#!/usr/bin/env python3
"""Assemble the single-file Philly3D page (society-hill-towers.html).

Everything the page needs — Three.js, the app, the styles, every packed data
blob — is inlined so one file serves philly3d.com and the GitHub Pages copy.
"""
import argparse, base64, json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "society-hill-towers.html"

ap = argparse.ArgumentParser()
ap.add_argument("--allow-missing", action="store_true", help="ship without an input instead of aborting")
args = ap.parse_args()

# Every data input with a byte floor (~80% of its Sep 2026 size). An interrupted
# pack or a moved file used to ship a city missing 180k buildings behind a
# cheerful "wrote N MB" and a clean "Ready"; now the build refuses.
REQUIRED = {
    "scene.json": 550_000, "meta.json": 10_000, "about_body.html": 3_000,
    "dem.json": 120_000, "dem_wide.json": 350_000, "dem_south.json": 120_000, "dem_city.json": 620_000,
    "dem_nw.json": 140_000, "wwb.json": 250, "wide_walls.b64": 100_000, "city_limit.json": 2_500, "wide_names.json": 3_000, "facade_palette.json": 300,
    "wide.b64": 4_800_000, "city.b64": 8_200_000, "outskirts.b64": 1_640_000, "storefronts.b64": 40_000, "trees.b64": 420_000, "poles.b64": 1_300_000, "traffic.b64": 100_000,
    "street_labels.json": 70_000, "street_sdf.json": 1_200_000, "tree_names.json": 8_000, "places.json": 12_000,
    "overpasses.json": 80_000, "nw_parks.json": 45_000, "nw_water.json": 55_000, "parking_south.json": 9_000,
    "towers.json": 4_000,
}
MAX_HTML = 75_000_000   # runaway-growth tripwire, raised from 25 MB on 2026-09-02 for the roof, colour and storefront passes (the page was ~25 MB; the old 16 MB artifact cap is long moot)
# Packed int16 blobs are stored byte-planar (header, all low bytes, all high
# bytes): DEFLATE then sees two smooth streams instead of one interleaved mess,
# 22% off the gzipped page with no packer change. app.js's unb64() re-interleaves.
# traffic.b64 grows 5% shuffled (short deltas), so it stays interleaved.
PLANAR = {"wide.b64": "WIDE", "city.b64": "CITY", "outskirts.b64": "OUTSKIRTS", "trees.b64": "TREES", "poles.b64": "POLES", "storefronts.b64": "STOREFRONTS"}
SIZES = []   # (label, bytes) for the report

def path_of(name):
    p = ROOT / name
    if not p.exists():
        if args.allow_missing:
            print(f"WARNING: {name} missing, shipping without it")
            return None
        sys.exit(f"FATAL: missing input {p} (pass --allow-missing to ship without it)")
    n = p.stat().st_size
    floor = REQUIRED.get(name, 0)
    if n < floor and not args.allow_missing:
        sys.exit(f"FATAL: {name} is {n:,} bytes, below its {floor:,}-byte floor: half-written pack? (--allow-missing overrides)")
    return p

def text_of(name, default):
    p = path_of(name)
    return p.read_text(encoding="utf-8").strip() if p else default

def dem_of(name, ndigits):
    """DEM grids: rounded (10 cm is invisible on a 25-150 m grid) and compact."""
    p = path_of(name)
    if not p:
        return "null"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["rows"] = [[None if v is None else round(v, ndigits) for v in row] for row in d["rows"]]
    return json.dumps(d, separators=(",", ":"))

def blob_of(name):
    """A packed base64 blob, byte-plane shuffled when PLANAR says so."""
    text = text_of(name, "")
    if text and name in PLANAR:
        raw = base64.b64decode(text)
        if len(raw) < 16 or (len(raw) - 16) % 2:
            sys.exit(f"FATAL: {name} body is not a 16-byte header + int16 body")
        body = raw[16:]
        text = base64.b64encode(raw[:16] + body[0::2] + body[1::2]).decode("ascii")
    return text

# Every data const ships as its own <script>, so the veil can count the bytes as
# they land (the PG block below); the split is only ever at a const boundary,
# never inside a base64 string. Top-level const/let in classic scripts share one
# global lexical scope, so app.js sees them exactly as it did from the single tag.
DATA_PARTS = []   # (label, js) in page order

def part(label, js):
    DATA_PARTS.append((label, js))

def const(label, js):
    SIZES.append((label, len(js)))
    part(label, f"const {label} = {js};\n")

def let_blob(label, name):
    b64 = blob_of(name)
    SIZES.append((label, len(b64)))
    part(label, f'let {label} = "{b64}";\n')

template = (ROOT / "template.html").read_text(encoding="utf-8")
css = (ROOT / "style.css").read_text(encoding="utf-8")
three = (ROOT / "three.min.js").read_text(encoding="utf-8")
# Three.js is pinned: r152+ removed outputEncoding/sRGBEncoding and turned on
# colour management, and app.js's ~250 colour constants are tuned to r149's
# legacy pipeline. A drop-in upgrade throws or repaints the city; see the note
# beside renderer.outputEncoding in app.js before changing this.
THREE_REV = "149"
m = re.search(r'"use strict";const e="(\d+)"', three)
if not m or m.group(1) != THREE_REV:
    sys.exit(f"FATAL: three.min.js is r{m.group(1) if m else '?'}, expected r{THREE_REV} (see the pin note in build.py)")
app = (ROOT / "app.js").read_text(encoding="utf-8")

scene = json.loads(path_of("scene.json").read_text(encoding="utf-8"))   # through the floor check like every other input
meta_path = path_of("meta.json")   # tower facts + landmark research, written by hand after workflow
meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path else {}
about_path = path_of("about_body.html")
about_body = about_path.read_text(encoding="utf-8") if about_path else "<p>Model of the towers and surrounding blocks.</p>"

part("B64_PLANAR", "const B64_PLANAR = " + json.dumps({v: 1 for v in PLANAR.values()} | {"TRAFFIC": 0}, separators=(",", ":")) + ";\n")
const("SCENE_DATA", json.dumps(scene, separators=(",", ":")))
const("META", json.dumps(meta, separators=(",", ":")))
const("DEM", dem_of("dem.json", 2))            # USGS NED 10 m grid, meters ASL, local 25 m cells
const("DEM_WIDE", dem_of("dem_wide.json", 1))
let_blob("WIDE_B64", "wide.b64")
let_blob("WIDE_WALLS_B64", "wide_walls.b64")
const("DEM_SOUTH", dem_of("dem_south.json", 1))
const("WWB_PTS", text_of("wwb.json", "null"))
const("WIDE_NAMES", text_of("wide_names.json", "null"))
# far ring: the rest of Philadelphia (city.b64 at 0.7 m units + 150 m DEM)
const("DEM_CITY", dem_of("dem_city.json", 1))
let_blob("CITY_B64", "city.b64")
# the towns across the city line (outskirts.b64 at 1.0 m units, pack_outskirts.py) and the
# flight limit (city_limit.json: the city line buffered 2 km, fetch_boundary.py)
let_blob("OUTSKIRTS_B64", "outskirts.b64")
# the storefronts (bake_storefronts.py): OSM shops on the facade edges that face the street
let_blob("STOREFRONTS_B64", "storefronts.b64")
const("CITY_LIMIT", text_of("city_limit.json", "null"))
# Tier-1 facade pass: sampled roof-color palette (raw sRGB; app divides for the legacy color pipeline)
const("FACADE_PAL", text_of("facade_palette.json", "null"))
# street-name labels (bake_street_labels.py — the packed road formats carry no names)
const("ST_LABELS", text_of("street_labels.json", "null"))
# real street trees (PPR Tree Inventory via fetch_trees.py / pack_trees.py)
let_blob("TREES_B64", "trees.b64")
const("TREE_NAMES", text_of("tree_names.json", "null"))
# historic districts + neighborhood labels (fetch_places.py / bake_places.py)
const("PLACES", text_of("places.json", "null"))
# street-name SDF atlas (bake_street_sdf.py — crisp lettering at any zoom)
sdf = text_of("street_sdf.json", "null")
SIZES.append(("ST_SDF", len(sdf)))
part("ST_SDF", "let ST_SDF = " + sdf + ";\n")
# elevated roads + the Vine Street cut (bake_overpasses.py from the raw OSM dumps)
const("OVERPASSES", text_of("overpasses.json", "null"))
# typical traffic volumes (fetch_traffic.py / bake_traffic.py — PennDOT AADT on OSM ways)
let_blob("TRAFFIC_B64", "traffic.b64")
# NW hills patch: 50 m DEM (fetch_dem_nw.py, border pre-feathered to dem_city),
# PPR parkland boundaries and full-fidelity creek/canal rings (fetch_nw_parks.py / fetch_nw_water.py)
const("DEM_NW", dem_of("dem_nw.json", 1))
const("NW_PARKS", text_of("nw_parks.json", "null"))
# the sports complex's surface lots (fetch_parking.py), asphalt flats under the outer districts
const("PARKING_SOUTH", text_of("parking_south.json", "null"))
# the Center City towers' facade archetypes, crowns and night accents (bake_towers.py), joined by position
const("TOWERS", text_of("towers.json", "null"))
const("NW_WATER", text_of("nw_water.json", "null"))
# streetlights (Streets Department pole inventory, fetch_poles.py / pack_poles.py)
let_blob("POLES_B64", "poles.b64")

# Download progress. Nothing used to move on the veil until the whole page had
# arrived and parsed. PG() rewrites the veil's load line, and a PG(i, n) tick
# follows every data chunk, running as the parser reaches it, so the line
# advances with the bytes. The transfer maps to 0-70%; app.js's build steps take
# the line from there.
PG_JS = ("window.PG = function (i, n) { var l = document.getElementById('loadmsg'); "
         "if (l) l.textContent = 'Downloading Philadelphia, ' + Math.round(i / n * 70) + '%'; };")
data_total = sum(len(js.encode("utf-8")) for _, js in DATA_PARTS)
data_html, done = [], 0
for label, js in DATA_PARTS:
    done += len(js.encode("utf-8"))
    data_html.append(f"<script>\n{js}</script>\n<script>PG({done}, {data_total})</script>")
data_js = "\n".join(data_html)

# brand icons inlined as data: URIs in the head (brand/make_brand.py fills dist/)
BRAND = ROOT / "brand" / "dist"
def brand_b64(name):
    p = BRAND / name
    if not p.exists():
        sys.exit(f"FATAL: missing {p} (run brand/make_brand.py)")
    return base64.b64encode(p.read_bytes()).decode("ascii")
fav_svg_b64 = brand_b64("favicon.svg")
fav_32_b64 = brand_b64("favicon-32.png")
touch_b64 = brand_b64("apple-touch-icon.png")

# </script> inside embedded JS strings would terminate the tag early
for name, blob in (("three", three), ("pg", PG_JS), ("app", app), ("css", css), ("about", about_body),
                   ("favicon_svg_b64", fav_svg_b64), ("favicon_32_b64", fav_32_b64), ("apple_icon_b64", touch_b64),
                   *(("data:" + label, js) for label, js in DATA_PARTS)):
    if re.search(r"</script", blob, re.I):
        sys.exit(f"FATAL: '</script' found inside {name} blob")

page = (template
        .replace("{{CSS}}", css)
        .replace("{{ABOUT_BODY}}", about_body)
        .replace("{{THREE}}", three)
        .replace("{{PG}}", "<script>" + PG_JS + "</script>")
        .replace("{{DATA}}", data_js)
        .replace("{{APP}}", app)
        .replace("{{FAVICON_SVG_B64}}", fav_svg_b64)
        .replace("{{FAVICON_32_B64}}", fav_32_b64)
        .replace("{{APPLE_ICON_B64}}", touch_b64))

left = re.search(r"\{\{[A-Z_0-9]+\}\}", page)
if left:
    sys.exit(f"FATAL: unsubstituted placeholder {left.group(0)} in the page")
if len(page.encode("utf-8")) > MAX_HTML:
    sys.exit(f"FATAL: page is {len(page.encode('utf-8')):,} bytes, over the {MAX_HTML:,} tripwire (raise MAX_HTML if this growth is intended)")

OUT.write_text(page, encoding="utf-8")
size = OUT.stat().st_size

# the report: what went in, and how the page moved against the committed build
SIZES += [("three.min.js", len(three)), ("app.js", len(app)), ("style.css", len(css))]
for label, n in sorted(SIZES, key=lambda t: -t[1]):
    if n >= 50_000:
        print(f"  {label:14s} {n:>12,d}")
try:
    prev = int(subprocess.run(["git", "cat-file", "-s", "HEAD:3d-model/society-hill-towers.html"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip())
    delta = f" ({size - prev:+,d} bytes vs HEAD)"
except Exception:
    delta = ""
print(f"wrote {OUT} ({size/1e6:.2f} MB){delta}")
