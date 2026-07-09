#!/usr/bin/env python3
"""
parse_report_pdf.py — Extract a new month's picks directly from the Top
Ideas PDF, with no manual transcription and no AI in the loop.

HOW IT WORKS
    Oppenheimer's report has the same two-part structure every month:
    1. Analyst write-ups: "<Coverage Area>  <Analyst Name>" followed by
       "<Company> (<TICKER> – <Rating>), $<PriceTarget> Price Target"
    2. A price table near the back ("OPCO Top Ideas: <Month> <Year>") with
       the actual as-of stock price for every ticker in one place.

    This script finds each name from data/known_analysts.json in the
    write-up section, grabs the ticker + price target that follows it,
    then looks up that ticker's real price in the back table. It does NOT
    use any AI/LLM — it's plain text pattern matching, so it runs the same
    way every time, including inside a GitHub Action with no Claude access.

SAFETY
    This is intentionally conservative: if an analyst from the known
    roster can't be matched to a pick, or a matched ticker isn't found in
    the price table, that row is flagged rather than guessed at. The
    script exits non-zero if anything was flagged, which is what makes
    the GitHub Action open a Pull Request for a human to check instead of
    silently pushing to the live site.

USAGE
    python scripts/parse_report_pdf.py new_report.pdf --report-key 2026-07 --report-label "Jul-Aug 2026"
    python scripts/parse_report_pdf.py new_report.pdf --report-key 2026-07 --out 2026-07.csv

    If --report-key is omitted, the script tries to infer it from the
    PDF's cover date.
"""
import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

MONTHS = {m: i + 1 for i, m in enumerate(
    ['January', 'February', 'March', 'April', 'May', 'June',
     'July', 'August', 'September', 'October', 'November', 'December']
)}

DASH = r'[\u2013\u2014\-]'  # en dash, em dash, hyphen — reports use these inconsistently


def pdf_to_text(pdf_path):
    result = subprocess.run(
        ['pdftotext', '-layout', str(pdf_path), '-'],
        capture_output=True, text=True, check=True
    )
    return result.stdout


def load_roster():
    sector_map = json.loads((DATA_DIR / "sector_map.json").read_text())
    aliases = json.loads((DATA_DIR / "name_aliases.json").read_text()) if (DATA_DIR / "name_aliases.json").exists() else {}
    canonical_names = list(sector_map.get('group', {}).keys())
    # roster maps every known spelling (canonical + alias) -> canonical name
    roster = {name: name for name in canonical_names}
    for alias, canonical in aliases.items():
        roster[alias] = canonical
    # sort longest-first so "Suraj Kalia, CFA" matches before the shorter "Suraj Kalia"
    return dict(sorted(roster.items(), key=lambda kv: -len(kv[0])))


def split_sections(text):
    """Split the report into the write-up section and the back price table."""
    m = re.search(r'OPCO Top Ideas:\s*(\w+)\s+(\d{4})', text)
    if not m:
        return text, "", None, None
    table_start = m.start()
    return text[:table_start], text[table_start:], m.group(1), m.group(2)


def infer_report_key(text, table_month, table_year):
    # Prefer the report's own "Month Year" from the price table title
    if table_month and table_month in MONTHS:
        return f"{table_year}-{MONTHS[table_month]:02d}"
    # fall back to the cover page's date line, e.g. "September 17, 2025"
    m = re.search(r'\b(' + '|'.join(MONTHS) + r')\s+\d{1,2},\s*(\d{4})', text)
    if m:
        return f"{m.group(2)}-{MONTHS[m.group(1)]:02d}"
    return None


def parse_price_table(table_text):
    """Return {ticker: (price, price_target_row_price)} and the as-of date string."""
    date_match = re.search(r'\n\s*(\d{1,2}/\d{1,2}/\d{2,4})\s+52-Week', table_text)
    as_of = date_match.group(1) if date_match else None

    prices = {}
    # e.g. "ABT Abbott Labs                O          131.33   141.23 110.86 Dec ..."
    row_re = re.compile(
        r'^([A-Z][A-Z0-9.]{0,5})\s+(.+?)\s+([OU])\s+([\d,]+\.\d+|\d+)\s+'
    )
    for line in table_text.splitlines():
        m = row_re.match(line.strip())
        if m:
            ticker = m.group(1)
            price = float(m.group(4).replace(',', ''))
            prices[ticker] = price
    return prices, as_of


def parse_writeups(writeup_text, roster):
    """Find each roster analyst's pick: (canonical_name, company, ticker, rating, price_target)."""
    # Anchor on the distinctive "(TICKER – O), $123 Price Target" fingerprint first —
    # company names sometimes have their own parentheticals (e.g. "Maplebear Inc.
    # (Instacart) (CART – O)"), so we can't rely on the company-name text alone.
    pick_re = re.compile(
        r'\(([A-Z][A-Z0-9.]{0,5})\s*' + DASH + r'\s*([OU])\)\s*,?\s*\$?([\d,]+)\s*Price Target',
    )

    found = {}
    not_found = []
    for spelling, canonical in roster.items():
        if canonical in found:
            continue  # already matched via a different spelling
        # find the LAST occurrence of this exact name (avoids matching a name that
        # appears earlier as plain narrative text, e.g. in "changes from last month")
        matches = [m for m in re.finditer(re.escape(spelling), writeup_text)]
        if not matches:
            continue
        name_end = matches[-1].end()
        window = writeup_text[name_end:name_end + 500]
        pm = pick_re.search(window)
        if not pm:
            not_found.append(canonical)
            continue
        ticker, rating, price_target = pm.groups()
        # company name is whatever sits between the analyst name and the ticker
        # fingerprint; the real name is the last chunk after splitting on the
        # column-gap (2+ spaces) that separates it from the coverage-area label
        company_raw = window[:pm.start()]
        chunks = [c.strip() for c in re.split(r' {2,}', company_raw) if c.strip()]
        company = chunks[-1] if chunks else company_raw.strip()
        found[canonical] = {
            'company': company,
            'ticker': ticker,
            'rating': rating,
            'price_target': price_target.replace(',', ''),
        }
    return found, not_found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pdf_path')
    ap.add_argument('--report-key', default=None, help='e.g. 2026-07 (inferred from the PDF if omitted)')
    ap.add_argument('--report-label', default=None, help='e.g. "Jul-Aug 2026" (inferred if omitted)')
    ap.add_argument('--out', default=None, help='Output CSV path (defaults to <report-key>.csv)')
    args = ap.parse_args()

    text = pdf_to_text(args.pdf_path)
    writeup_text, table_text, table_month, table_year = split_sections(text)

    report_key = args.report_key or infer_report_key(text, table_month, table_year)
    if not report_key:
        sys.exit("Could not determine the report month — pass --report-key explicitly, e.g. --report-key 2026-07")

    report_label = args.report_label or (f"{table_month}-? {table_year}" if table_month else report_key)

    roster = load_roster()
    prices, as_of = parse_price_table(table_text)
    picks, not_found = parse_writeups(writeup_text, roster)

    rows = []
    price_missing = []
    for analyst, p in picks.items():
        price = prices.get(p['ticker'])
        if price is None:
            price_missing.append((analyst, p['ticker']))
        rows.append({
            'report_key': report_key,
            'report_label': report_label,
            'year': report_key.split('-')[0],
            'analyst': analyst,
            'company': p['company'],
            'ticker': p['ticker'],
            'rating': p['rating'],
            'price_target': p['price_target'],
            'stock_price': price if price is not None else '',
            'price_as_of': as_of or '',
        })

    rows.sort(key=lambda r: r['analyst'])
    out_path = Path(args.out) if args.out else ROOT / f"{report_key}.csv"
    with open(out_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['report_key', 'report_label', 'year', 'analyst',
                                          'company', 'ticker', 'rating', 'price_target',
                                          'stock_price', 'price_as_of'])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Parsed {len(rows)} picks from {args.pdf_path} -> {out_path}")
    print(f"Report: {report_key} ({report_label}), as-of date: {as_of or '(not found — check manually)'}")

    problems = False
    if not_found:
        problems = True
        print(f"\nWARNING: {len(not_found)} known analyst(s) had no pick found in this report:")
        for n in not_found:
            print(f"   - {n}")
        print("  (This is expected if they rotated off coverage this month — otherwise, check the PDF manually.)")

    if price_missing:
        problems = True
        print(f"\nWARNING: {len(price_missing)} ticker(s) matched in the write-ups but NOT found in the price table:")
        for analyst, ticker in price_missing:
            print(f"   - {analyst}: {ticker}")
        print("  These rows were written with a blank stock_price and will be skipped by add_report.py until fixed.")

    if as_of is None:
        problems = True
        print("\nWARNING: could not find an explicit as-of date in the price table (this happened once before, "
              "Sept 2025) — fill in price_as_of manually in the CSV before running add_report.py.")

    if problems:
        print("\nSome rows need a manual check before this is safe to merge. See warnings above.")
        sys.exit(1)

    print("\nNo issues detected. Safe to run: python scripts/add_report.py " + str(out_path))


if __name__ == "__main__":
    main()
