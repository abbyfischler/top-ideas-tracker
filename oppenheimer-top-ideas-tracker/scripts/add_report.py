#!/usr/bin/env python3
"""
add_report.py — Add a new month's Top Ideas report to the tracker.

WHAT THIS DOES
    1. Reads the new report's picks from a CSV or XLSX file you provide.
    2. Normalizes analyst names using data/name_aliases.json (fixes the kind
       of naming inconsistency Oppenheimer's own reports have had before —
       e.g. a stray sector prefix, or "Suraj Kalia, CFA" vs "Suraj Kalia").
    3. Appends the new rows to data/master_picks.csv (skipping any
       report_key + analyst pair that's already there, unless you pass --force).
    4. Rebuilds data/data.json by calling build_data.py, so index.html
       immediately reflects the new report.

INPUT FILE FORMAT
    Your new file needs these columns (case-insensitive, any column order):
        report_key      e.g. "2026-07"           (YYYY-MM, sorts chronologically)
        report_label    e.g. "Jul-Aug 2026"       (human-readable, shown in the UI)
        analyst         e.g. "Brian Schwartz"
        company         e.g. "Salesforce Inc."
        ticker          e.g. "CRM"
        stock_price     e.g. 312.40
        price_target    e.g. 380              (optional, leave blank if unknown)
        price_as_of     e.g. 7/20/26          (optional; M/D/YY)
        rating          e.g. O                (optional, not currently used in the UI)

    A CSV with just report_key, report_label, analyst, ticker, stock_price is
    enough to get a report into the tracker. If you're copying straight out
    of the PDF's summary table, that's usually the fastest way to build it —
    each analyst's line is "Ticker (Rating), $Price Target" plus the price
    table at the back of the report which has the actual stock price.

USAGE
    python scripts/add_report.py new_report.csv
    python scripts/add_report.py new_report.xlsx --sheet "All Picks"
    python scripts/add_report.py new_report.csv --force      (overwrite duplicates)
    python scripts/add_report.py new_report.csv --dry-run     (preview only, no writes)

AFTER RUNNING
    Open index.html (or push to GitHub) — the site rebuilds itself from
    data/data.json, no other steps needed. If you want a written summary of
    what changed, run:
        python scripts/generate_summary_report.py
"""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MASTER = DATA_DIR / "master_picks.csv"
COLUMNS = ['report_key', 'report_label', 'year', 'analyst', 'company', 'ticker',
           'rating', 'price_target', 'stock_price', 'price_as_of']


def load_aliases():
    path = DATA_DIR / "name_aliases.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def read_input_rows(path, sheet_name=None):
    """Read the new report file (csv or xlsx) into a list of dicts with lowercase keys."""
    path = Path(path)
    if path.suffix.lower() in ('.xlsx', '.xlsm'):
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb[sheet_name] if sheet_name else wb.active
        headers = [str(c.value).strip().lower() if c.value else '' for c in next(ws.iter_rows(min_row=1, max_row=1))]
        rows = []
        for r in ws.iter_rows(min_row=2, values_only=True):
            if all(v is None for v in r):
                continue
            rows.append({headers[i]: r[i] for i in range(len(headers)) if i < len(r)})
        return rows
    else:
        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            return [{k.strip().lower(): v for k, v in row.items()} for row in reader]


def normalize_row(row, aliases):
    def g(key, default=''):
        v = row.get(key, default)
        return '' if v is None else str(v).strip()

    analyst = g('analyst')
    analyst = aliases.get(analyst, analyst)
    report_key = g('report_key')
    year = g('year') or (report_key.split('-')[0] if '-' in report_key else '')

    return {
        'report_key': report_key,
        'report_label': g('report_label'),
        'year': year,
        'analyst': analyst,
        'company': g('company'),
        'ticker': g('ticker').upper(),
        'rating': g('rating') or 'O',
        'price_target': g('price_target'),
        'stock_price': g('stock_price'),
        'price_as_of': g('price_as_of'),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input_file', help='New report CSV or XLSX file')
    ap.add_argument('--sheet', default=None, help='Sheet name if input is XLSX (defaults to the active sheet)')
    ap.add_argument('--force', action='store_true', help='Overwrite existing rows for the same report_key+analyst')
    ap.add_argument('--dry-run', action='store_true', help='Preview changes without writing anything')
    args = ap.parse_args()

    aliases = load_aliases()
    raw_rows = read_input_rows(args.input_file, args.sheet)
    if not raw_rows:
        sys.exit(f"No rows found in {args.input_file}")

    new_rows = [normalize_row(r, aliases) for r in raw_rows]

    missing_required = [r for r in new_rows if not (r['report_key'] and r['analyst'] and r['ticker'] and r['stock_price'])]
    if missing_required:
        print(f"WARNING: {len(missing_required)} row(s) are missing report_key, analyst, ticker, or stock_price and will be skipped:")
        for r in missing_required[:10]:
            print("   -", r)
        new_rows = [r for r in new_rows if r not in missing_required]

    # load existing master rows to check for duplicates
    existing = []
    existing_keys = set()
    if MASTER.exists():
        with open(MASTER, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing.append(row)
                existing_keys.add((row['report_key'], row['analyst']))

    to_add = []
    skipped = []
    for r in new_rows:
        key = (r['report_key'], r['analyst'])
        if key in existing_keys and not args.force:
            skipped.append(r)
            continue
        to_add.append(r)

    print(f"Input file: {args.input_file}")
    print(f"  {len(new_rows)} usable rows parsed")
    print(f"  {len(to_add)} new rows to add")
    if skipped:
        print(f"  {len(skipped)} rows skipped (already present for that report_key+analyst — use --force to overwrite):")
        for r in skipped[:10]:
            print(f"     - {r['report_key']} / {r['analyst']} / {r['ticker']}")

    if args.dry_run:
        print("\n--dry-run set: no files were changed.")
        return

    if args.force:
        # remove any existing rows that are being overwritten
        overwrite_keys = {(r['report_key'], r['analyst']) for r in to_add}
        existing = [row for row in existing if (row['report_key'], row['analyst']) not in overwrite_keys]

    all_rows = existing + to_add
    all_rows.sort(key=lambda r: (r['report_key'], r['analyst']))

    with open(MASTER, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in all_rows:
            w.writerow({c: r.get(c, '') for c in COLUMNS})

    print(f"\nWrote {len(all_rows)} total rows to {MASTER}")

    # rebuild data.json
    print("\nRebuilding data/data.json ...")
    result = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_data.py')], cwd=ROOT)
    if result.returncode != 0:
        sys.exit("build_data.py failed — master_picks.csv was updated but data.json was not rebuilt.")

    print("\nRebuilding index.html ...")
    result = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_site.py')], cwd=ROOT)
    if result.returncode != 0:
        sys.exit("build_site.py failed — data.json was rebuilt but index.html was not.")

    print("\nDone. Open index.html to see the new report reflected, or commit + push to GitHub.")


if __name__ == "__main__":
    main()
