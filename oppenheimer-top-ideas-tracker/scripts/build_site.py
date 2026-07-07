#!/usr/bin/env python3
"""
build_site.py — Inject data/data.json into templates/index_template.html
to produce the final index.html at the repo root.

Why this exists: index.html embeds its data inline (rather than fetching
data.json at runtime) so the site works whether it's opened straight off
disk, served via GitHub Pages, or anything in between — no CORS surprises.

This is normally called automatically by add_report.py. Run it directly
only if you've hand-edited data/data.json and need to re-embed it, or if
you've edited css/style.css or js/script.js and want those picked up too
(index.html references them by relative path, so most CSS/JS edits don't
need a rebuild at all — only the embedded data does).

Usage:
    python scripts/build_site.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    data_path = ROOT / "data" / "data.json"
    template_path = ROOT / "templates" / "index_template.html"
    out_path = ROOT / "index.html"

    if not data_path.exists():
        raise SystemExit("data/data.json not found — run scripts/build_data.py first.")

    data_json = data_path.read_text()
    # sanity check it's valid JSON before embedding
    json.loads(data_json)

    template = template_path.read_text()
    if "__DATA_JSON__" not in template:
        raise SystemExit("templates/index_template.html is missing the __DATA_JSON__ placeholder.")

    output = template.replace("__DATA_JSON__", data_json)
    out_path.write_text(output)
    print(f"Wrote {out_path} ({len(output)/1024:.1f} KB)")


if __name__ == "__main__":
    main()
