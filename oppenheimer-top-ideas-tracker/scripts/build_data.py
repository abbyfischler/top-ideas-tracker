#!/usr/bin/env python3
"""
build_data.py — Regenerate data/data.json from data/master_picks.csv

This is the single script that turns the raw picks table into everything
the website (index.html) needs: per-analyst pick history, computed returns,
cumulative return series, calendar-year returns, and benchmark comparisons.

Run this any time master_picks.csv changes (usually via add_report.py,
which calls this automatically).

Usage:
    python scripts/build_data.py

Reads:
    data/master_picks.csv     - one row per analyst pick per report
    data/sector_map.json      - analyst -> {sector_group, sector_label}
    data/etf_map.json         - analyst -> {etf, label, r: [2023,2024,2025,2026]}
    data/spx_benchmark.json   - S&P 500 annual returns (universal fallback benchmark)

Writes:
    data/data.json             - the file index.html loads at runtime
"""
import csv
import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

SECTOR_ORDER = ['TECHNOLOGY', 'HEALTH CARE', 'INDUSTRIALS/ENERGY', 'FINANCIALS/CONSUMER']


def parse_date(s):
    """Parse an M/D/YY string into ISO YYYY-MM-DD. Returns None if unparseable."""
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        m, d, y = s.split('/')
        yr = int(y)
        yr += 2000 if yr < 100 else 0
        return datetime(yr, int(m), int(d)).strftime('%Y-%m-%d')
    except Exception:
        return None


def num(v):
    """Coerce a CSV cell to float, or None if blank/non-numeric."""
    if v is None:
        return None
    v = str(v).strip()
    if v == '':
        return None
    try:
        return float(v)
    except ValueError:
        return None


def load_master_picks():
    path = DATA_DIR / "master_picks.csv"
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        required = {'report_key', 'analyst', 'ticker', 'stock_price'}
        missing = required - set(reader.fieldnames or [])
        if missing:
            sys.exit(f"master_picks.csv is missing required columns: {missing}")
        for row in reader:
            rows.append(row)
    return rows


def build(rows, sector_map, etf_map, spx):
    # group rows by analyst, preserving chronological order via report_key (YYYY-MM sorts correctly)
    by_analyst = defaultdict(list)
    for row in rows:
        analyst = row['analyst'].strip()
        by_analyst[analyst].append({
            "report_key": row['report_key'].strip(),
            "report_label": row.get('report_label', '').strip(),
            "company": (row.get('company') or '').strip() or None,
            "ticker": (row.get('ticker') or '').strip() or None,
            "price_target": num(row.get('price_target')),
            "price": num(row.get('stock_price')),
            "date": parse_date(row.get('price_as_of')),
        })

    final = []
    for analyst, picks in by_analyst.items():
        picks.sort(key=lambda p: p['report_key'])
        hist = []
        for i, p in enumerate(picks):
            ret = None
            if i > 0:
                prev = picks[i - 1]
                if prev['ticker'] == p['ticker'] and prev['price'] not in (None, 0) and p['price'] is not None:
                    ret = round((p['price'] - prev['price']) / prev['price'], 4)
            hist.append({
                "report_key": p['report_key'], "report_label": p['report_label'], "date": p['date'],
                "ticker": p['ticker'], "company": p['company'], "price": p['price'],
                "price_target": p['price_target'], "return": ret,
                "new_pick": (i == 0) or (picks[i - 1]['ticker'] != p['ticker']),
            })

        cum = 1.0
        cum_series = []
        for h in hist:
            if h['return'] is not None:
                cum *= (1 + h['return'])
            cum_series.append(round(cum, 4))

        sec = sector_map.get('group', {}).get(analyst)
        lbl = sector_map.get('label', {}).get(analyst)
        etf = etf_map.get(analyst)

        entry = {
            "analyst": analyst,
            "sector_group": sec,
            "sector_label": lbl,
            "history": hist,
            "cum": cum_series,
            "total_return": round((cum - 1) * 100, 1),
            "etf": etf['etf'] if etf else None,
            "etf_label": etf['label'] if etf else None,
            "etf_returns": {str(2023 + i): etf['r'][i] for i in range(4)} if etf else None,
            "spx_returns": spx['returns'],
        }

        # trailing 12-report return
        last12 = hist[-12:]
        c = 1.0
        for row in last12:
            if row['return'] is not None:
                c *= (1 + row['return'])
        entry['trailing_return'] = round((c - 1) * 100, 1)

        # per-calendar-year returns (used for YTD, half-year splits, insights)
        by_year = defaultdict(list)
        for h in hist:
            if h['report_key']:
                by_year[h['report_key'][:4]].append(h)
        year_returns = {}
        for y in ('2023', '2024', '2025', '2026'):
            entries = by_year.get(y, [])
            if not entries:
                year_returns[y] = None
                continue
            c = 1.0
            any_ret = False
            for h in entries:
                if h['return'] is not None:
                    c *= (1 + h['return'])
                    any_ret = True
            year_returns[y] = round((c - 1) * 100, 1) if any_ret else None
        entry['year_returns'] = year_returns

        if hist:
            entry['latest_ticker'] = hist[-1]['ticker']
            entry['latest_price'] = hist[-1]['price']
            entry['latest_date'] = hist[-1]['date']
            entry['num_picks'] = len(hist)
        else:
            entry['latest_ticker'] = None
            entry['latest_price'] = None
            entry['latest_date'] = None
            entry['num_picks'] = 0

        final.append(entry)

    order = SECTOR_ORDER
    final.sort(key=lambda a: (order.index(a['sector_group']) if a['sector_group'] in order else 99, a['analyst']))
    return final


def main():
    rows = load_master_picks()
    sector_map = json.loads((DATA_DIR / "sector_map.json").read_text())
    etf_map = json.loads((DATA_DIR / "etf_map.json").read_text())
    spx = json.loads((DATA_DIR / "spx_benchmark.json").read_text())

    unmapped = sorted({r['analyst'].strip() for r in rows} - set(sector_map.get('group', {}).keys()))
    if unmapped:
        print("WARNING: the following analysts have no sector mapping in data/sector_map.json:")
        for u in unmapped:
            print("   -", u)
        print("They will still appear in the site, grouped last, with a blank sector label.")
        print("Add them to sector_map.json's \"group\" and \"label\" objects to classify them properly.\n")

    final = build(rows, sector_map, etf_map, spx)

    out_path = DATA_DIR / "data.json"
    out_path.write_text(json.dumps(final, separators=(',', ':')))

    total_picks = sum(len(a['history']) for a in final)
    print(f"Wrote {out_path}")
    print(f"  {len(final)} analysts, {total_picks} picks")
    all_dates = [h['date'] for a in final for h in a['history'] if h['date']]
    if all_dates:
        print(f"  date range: {min(all_dates)} to {max(all_dates)}")


if __name__ == "__main__":
    main()
