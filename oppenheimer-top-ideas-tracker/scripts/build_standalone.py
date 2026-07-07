#!/usr/bin/env python3
"""
build_standalone.py — Build a single, fully self-contained HTML file.

Unlike index.html (which links out to css/style.css and js/script.js —
correct for GitHub Pages, but fragile if someone only copies the .html
file by itself), this inlines everything into one file with zero external
dependencies. Safe to rename, move, email, or drop anywhere on its own.

Usage:
    python scripts/build_standalone.py
    python scripts/build_standalone.py --out my_tracker.html
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='standalone.html')
    args = ap.parse_args()

    template = (ROOT / "templates" / "index_template.html").read_text()
    css = (ROOT / "css" / "style.css").read_text()
    js = (ROOT / "js" / "script.js").read_text()
    data_json = (ROOT / "data" / "data.json").read_text()
    json.loads(data_json)  # sanity check

    output = template.replace(
        '<link rel="stylesheet" href="css/style.css">',
        f'<style>\n{css}\n</style>'
    ).replace(
        '<script src="js/script.js"></script>',
        f'<script>\n{js}\n</script>'
    ).replace('__DATA_JSON__', data_json)

    out_path = ROOT / args.out
    out_path.write_text(output)
    print(f"Wrote {out_path} ({len(output)/1024:.1f} KB) — fully self-contained, no external files needed.")


if __name__ == "__main__":
    main()
