#!/usr/bin/env python3
"""Check that handoff.md's file table covers every build input and every script.

Parses the `ROOT / "..."` inputs out of build.py, lists 3d-model/*.py, and looks for
each name inside the "What's in `3d-model/`" section of handoff.md (up to the next
level-2 heading). Exits non-zero naming anything the table does not mention.
Standard library only; run from anywhere:

    python3 3d-model/docs_check.py [--build PATH] [--handoff PATH]
"""
import argparse
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SECTION_HEAD = re.compile(r"^##\s+What's in\s+`?3d-model/?`?", re.I)
# build.py names its inputs as quoted file names: `ROOT / "x.json"`, `path_of("x.b64")`,
# `dem_of("dem_nw.json", 1)`, `let_blob("CITY_B64", "city.b64")` and the brand icons
ROOT_INPUT = re.compile(r"""(["'])([A-Za-z0-9_./-]+\.(?:json|b64|html|css|js|ttf|png|svg|ico))\1""")


def build_inputs(build_py: pathlib.Path):
    text = build_py.read_text(encoding="utf-8")
    names = {m.group(2) for m in ROOT_INPUT.finditer(text)}
    names.discard("society-hill-towers.html")            # the output, not an input
    return sorted(n for n in names if not n.startswith("3d-model/"))


def scripts(folder: pathlib.Path):
    return sorted(p.name for p in folder.glob("*.py"))


def file_table(handoff: pathlib.Path) -> str:
    lines = handoff.read_text(encoding="utf-8").split("\n")
    out, inside = [], False
    for line in lines:
        if SECTION_HEAD.match(line):
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if inside:
            out.append(line)
    if not out:
        sys.exit(f"docs_check: no \"What's in `3d-model/`\" section in {handoff}")
    return "\n".join(out)


def mentioned(name: str, table: str) -> bool:
    # a name counts when it appears inside a backticked span of the section
    for span in re.findall(r"`([^`]+)`", table):
        if name in span:
            return True
    return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--build", type=pathlib.Path, default=HERE / "build.py")
    ap.add_argument("--handoff", type=pathlib.Path, default=HERE.parent / "handoff.md")
    ap.add_argument("--folder", type=pathlib.Path, default=HERE,
                    help="folder whose *.py files must be documented (default: this one)")
    args = ap.parse_args(argv)

    for p in (args.build, args.handoff):
        if not p.exists():
            print(f"docs_check: missing {p}", file=sys.stderr)
            return 2

    table = file_table(args.handoff)
    inputs = build_inputs(args.build)
    pys = scripts(args.folder)
    missing_inputs = [n for n in inputs if not mentioned(n, table)]
    missing_scripts = [n for n in pys if not mentioned(n, table)]

    if missing_inputs or missing_scripts:
        if missing_inputs:
            print("build.py inputs not in handoff.md's file table:", file=sys.stderr)
            for n in missing_inputs:
                print(f"  {n}", file=sys.stderr)
        if missing_scripts:
            print("scripts not in handoff.md's file table:", file=sys.stderr)
            for n in missing_scripts:
                print(f"  {n}", file=sys.stderr)
        return 1

    print(f"docs_check: ok ({len(inputs)} build inputs, {len(pys)} scripts all documented)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
