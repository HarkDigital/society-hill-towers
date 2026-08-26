#!/usr/bin/env python3
"""Assemble the single-file Society Hill Towers artifact page."""
import base64, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "society-hill-towers.html"

template = (ROOT / "template.html").read_text(encoding="utf-8")
css = (ROOT / "style.css").read_text(encoding="utf-8")
three = (ROOT / "three.min.js").read_text(encoding="utf-8")
app = (ROOT / "app.js").read_text(encoding="utf-8")

scene = json.loads((ROOT / "scene.json").read_text(encoding="utf-8"))
meta_path = ROOT / "meta.json"   # tower facts + landmark research, written by hand after workflow
meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

about_path = ROOT / "about_body.html"
about_body = about_path.read_text(encoding="utf-8") if about_path.exists() else "<p>Model of the towers and surrounding blocks.</p>"

dem_path = ROOT / "dem.json"   # USGS NED 10 m grid, meters ASL, local 25 m cells
dem = json.loads(dem_path.read_text(encoding="utf-8")) if dem_path.exists() else None
if dem:
    dem["rows"] = [[None if v is None else round(v, 2) for v in row] for row in dem["rows"]]
data_js = (
    "const SCENE_DATA = " + json.dumps(scene, separators=(",", ":")) + ";\n"
    + "const META = " + json.dumps(meta, separators=(",", ":")) + ";\n"
    + "const DEM = " + json.dumps(dem, separators=(",", ":")) + ";\n"
)
demw_path = ROOT / "dem_wide.json"
demw = json.loads(demw_path.read_text(encoding="utf-8")) if demw_path.exists() else None
if demw:
    demw["rows"] = [[None if v is None else round(v, 1) for v in row] for row in demw["rows"]]
wide_path = ROOT / "wide.b64"
wide_b64 = wide_path.read_text(encoding="utf-8").strip() if wide_path.exists() else ""
data_js += ("const DEM_WIDE = " + json.dumps(demw, separators=(",", ":")) + ";\n"
            + "let WIDE_B64 = \"" + wide_b64 + "\";\n")
dems_path = ROOT / "dem_south.json"
dems = json.loads(dems_path.read_text(encoding="utf-8")) if dems_path.exists() else None
if dems:
    dems["rows"] = [[None if v is None else round(v, 1) for v in row] for row in dems["rows"]]
wwb_path = ROOT / "wwb.json"
data_js += ("const DEM_SOUTH = " + json.dumps(dems, separators=(",", ":")) + ";\n"
            + "const WWB_PTS = " + (wwb_path.read_text(encoding="utf-8").strip() if wwb_path.exists() else "null") + ";\n")
names_path = ROOT / "wide_names.json"
data_js += "const WIDE_NAMES = " + (names_path.read_text(encoding="utf-8") if names_path.exists() else "null") + ";\n"
# far ring: the rest of Philadelphia (city.b64 at 0.7 m units + 150 m DEM)
demc_path = ROOT / "dem_city.json"
demc = json.loads(demc_path.read_text(encoding="utf-8")) if demc_path.exists() else None
if demc:
    demc["rows"] = [[None if v is None else round(v, 1) for v in row] for row in demc["rows"]]
city_path = ROOT / "city.b64"
city_b64 = city_path.read_text(encoding="utf-8").strip() if city_path.exists() else ""
data_js += ("const DEM_CITY = " + json.dumps(demc, separators=(",", ":")) + ";\n"
            + "let CITY_B64 = \"" + city_b64 + "\";\n")
# Tier-1 facade pass: sampled roof-color palette (raw sRGB; app divides for the
# legacy color pipeline)
fpal_path = ROOT / "facade_palette.json"
fpal = json.loads(fpal_path.read_text(encoding="utf-8")) if fpal_path.exists() else None
data_js += "const FACADE_PAL = " + json.dumps(fpal, separators=(",", ":")) + ";\n"
# street-name labels (baked by bake_street_labels.py from the scene jsons —
# the packed road formats carry no names)
stl_path = ROOT / "street_labels.json"
data_js += "const ST_LABELS = " + (stl_path.read_text(encoding="utf-8").strip() if stl_path.exists() else "null") + ";\n"
# real street trees (PPR Tree Inventory via fetch_trees.py / pack_trees.py)
trees_path = ROOT / "trees.b64"
data_js += 'let TREES_B64 = "' + (trees_path.read_text(encoding="utf-8").strip() if trees_path.exists() else "") + '";\n'
tn_path = ROOT / "tree_names.json"
data_js += "const TREE_NAMES = " + (tn_path.read_text(encoding="utf-8").strip() if tn_path.exists() else "null") + ";\n"
# historic districts + neighborhood labels (fetch_places.py / bake_places.py)
places_path = ROOT / "places.json"
data_js += "const PLACES = " + (places_path.read_text(encoding="utf-8").strip() if places_path.exists() else "null") + ";\n"
# street-name SDF atlas (bake_street_sdf.py — crisp lettering at any zoom)
sdf_path = ROOT / "street_sdf.json"
data_js += "let ST_SDF = " + (sdf_path.read_text(encoding="utf-8").strip() if sdf_path.exists() else "null") + ";\n"
# elevated roads + the Vine Street cut (bake_overpasses.py from the raw OSM dumps)
ovp_path = ROOT / "overpasses.json"
data_js += "const OVERPASSES = " + (ovp_path.read_text(encoding="utf-8").strip() if ovp_path.exists() else "null") + ";\n"
# typical traffic volumes (fetch_traffic.py / bake_traffic.py — PennDOT AADT on OSM ways)
tr_path = ROOT / "traffic.b64"
data_js += 'let TRAFFIC_B64 = "' + (tr_path.read_text(encoding="utf-8").strip() if tr_path.exists() else "") + '";\n'

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
for name, blob in (("three", three), ("data", data_js), ("app", app), ("css", css), ("about", about_body),
                   ("favicon_svg_b64", fav_svg_b64), ("favicon_32_b64", fav_32_b64), ("apple_icon_b64", touch_b64)):
    if re.search(r"</script", blob, re.I):
        sys.exit(f"FATAL: '</script' found inside {name} blob")

page = (template
        .replace("{{CSS}}", css)
        .replace("{{ABOUT_BODY}}", about_body)
        .replace("{{THREE}}", three)
        .replace("{{DATA}}", data_js)
        .replace("{{APP}}", app)
        .replace("{{FAVICON_SVG_B64}}", fav_svg_b64)
        .replace("{{FAVICON_32_B64}}", fav_32_b64)
        .replace("{{APPLE_ICON_B64}}", touch_b64))

OUT.write_text(page, encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB)")
