# Oppenheimer Top Ideas — Analyst Coverage Tracker

A static, no-backend website that tracks every analyst's monthly stock pick
from Oppenheimer's "Top Ideas" reports, compounds their returns, and compares
them against a sector ETF (where we have one) and the S&P 500 (always).

**Live view:** just open `index.html` in a browser, or host it on GitHub Pages
(instructions below). `index.html` links out to `css/style.css` and
`js/script.js`, so **keep those two folders sitting right next to it** —
if you only copy or email the single `index.html` file by itself, the page
will load with no styling (you'll see raw unstyled text and an enormous
unstyled circle where the logo mark should be — that's this exact problem).

If you want one file you can rename, move, or email around with zero risk of
that happening, run `python scripts/build_standalone.py` — it inlines
everything (CSS, JS, and data) into a single file with no dependencies at
all. Slightly bigger, but foolproof.

---

## What's in this folder

```
├── index.html              ← the actual website. Open this.
├── css/style.css           ← all styling
├── js/script.js            ← all interactivity (filtering, sorting, charts, insights)
├── templates/
│   └── index_template.html ← skeleton index.html is generated from (has a __DATA_JSON__ placeholder)
├── data/
│   ├── master_picks.csv    ← THE SOURCE OF TRUTH. One row per analyst pick per report.
│   ├── sector_map.json     ← analyst → sector group + coverage-area label
│   ├── etf_map.json        ← analyst → sector ETF ticker + annual returns (partial coverage)
│   ├── spx_benchmark.json  ← S&P 500 annual returns (universal benchmark, all analysts)
│   ├── name_aliases.json   ← known analyst-name inconsistencies → canonical name
│   └── data.json           ← GENERATED — what index.html actually loads. Don't hand-edit this.
├── scripts/
│   ├── build_data.py       ← master_picks.csv + maps → data/data.json
│   ├── build_site.py       ← data/data.json + template → index.html (linked css/js)
│   ├── build_standalone.py ← data/data.json + template → one self-contained .html file
│   ├── add_report.py       ← the script you'll actually run each month (see below)
│   └── generate_summary_report.py ← makes a Word doc summary you can send around
└── requirements.txt
```

**You should basically never need to touch `index.html`, `css/`, `js/`, or
`data/data.json` directly.** The one file that matters is
`data/master_picks.csv`, and the one script you run is `add_report.py`.

---

## Adding next month's report (the main workflow)

When Oppenheimer's next Top Ideas report comes out (July, August, whatever),
here's the whole process:

### 1. Build a small CSV of that month's picks

Create a file (name it anything, e.g. `2026-07.csv`) with these columns:

| Column | Required? | Example | Notes |
|---|---|---|---|
| `report_key` | **yes** | `2026-07` | `YYYY-MM` — this is what makes reports sort chronologically. Use the report's *first* month if it spans two (e.g. "Jul-Aug 2026" → `2026-07`). |
| `report_label` | recommended | `Jul-Aug 2026` | Human-readable, shown in the UI. |
| `analyst` | **yes** | `Brian Schwartz` | Use the analyst's name as it appears in the report. If a report is inconsistent about it (it has happened before — sector-name prefixes, credential suffixes), add the mapping to `data/name_aliases.json` and it'll be normalized automatically. |
| `company` | recommended | `Salesforce Inc.` | Shown in the pick history table. |
| `ticker` | **yes** | `CRM` | |
| `stock_price` | **yes** | `312.40` | The report's cover price for that pick. This is what all the return math is built on. |
| `price_target` | optional | `380` | Shown in the detail table if present. |
| `price_as_of` | optional | `7/20/26` | M/D/YY. If the report doesn't print a specific date (this has happened once already — Sept 2025), just leave it blank or use the report's disseminated date. |
| `rating` | optional | `O` | Not currently used anywhere in the UI. |

The fastest way to build this: open the new PDF, go through each analyst's
write-up (ticker + rating + price target), then cross-reference the
price table near the end of the report (it has the actual stock price and
report date for every ticker in one place).

A minimal CSV only needs `report_key`, `report_label`, `analyst`, `ticker`,
`stock_price` — everything else is optional.

### 2. Run the update script

```bash
cd path/to/this/folder
python scripts/add_report.py 2026-07.csv
```

This will:
- normalize analyst names using `data/name_aliases.json`
- skip any row that's already in `master_picks.csv` for that report + analyst (so it's safe to re-run)
- append the new rows to `data/master_picks.csv`
- regenerate `data/data.json`
- regenerate `index.html`

You'll see a summary of how many rows were added/skipped. Use `--dry-run`
first if you want to preview without writing anything, and `--force` if you
need to overwrite a report that's already in there (e.g. you fixed a typo).

```bash
python scripts/add_report.py 2026-07.csv --dry-run     # preview only
python scripts/add_report.py 2026-07.csv --force        # overwrite existing rows for that month
python scripts/add_report.py 2026-07.xlsx --sheet "All Picks"   # xlsx input works too
```

### 3. Check the output

Open `index.html` — the new month should show up immediately (new "latest
pick" per analyst, updated returns, new period tab if it's a new year, etc.)
No further steps needed for local viewing.

### 4. If a new analyst shows up

`build_data.py` will print a warning listing any analyst it doesn't recognize
from `data/sector_map.json`. To classify them properly, add two entries:

```jsonc
// data/sector_map.json
{
  "group": { "...": "...", "New Analyst Name": "TECHNOLOGY" },
  "label": { "...": "...", "New Analyst Name": "Coverage Area Name" }
}
```

Valid `"group"` values: `TECHNOLOGY`, `HEALTH CARE`, `INDUSTRIALS/ENERGY`,
`FINANCIALS/CONSUMER`. Then re-run `python scripts/build_data.py &&
python scripts/build_site.py` (or just re-run `add_report.py`, it does both).

### 5. If you get sector ETF data for an analyst who doesn't have one yet

Add an entry to `data/etf_map.json`:

```jsonc
{
  "Analyst Name": {"etf": "XLK", "label": "Coverage area name", "r": [2023_return, 2024_return, 2025_return, 2026_return]}
}
```

Use `null` for any year you don't have a number for (e.g. `[58.47, 23.4, null, null]`).
Every analyst already gets compared to the S&P 500 automatically — this just
adds a more specific sector-level comparison on top.

### 6. Updating the S&P 500 benchmark

`data/spx_benchmark.json` has full-year S&P 500 returns for 2023–2025 and a
year-to-date figure for 2026. Update the 2026 number periodically (e.g. at
each quarter, or whenever you regenerate a report) so the comparison stays
current — it won't update itself.

---

## Generating a summary report to send around

```bash
python scripts/generate_summary_report.py
```

This produces a Word document (`.docx`) in the project folder summarizing the
current year's performance — top/bottom performers, sector scoreboard, idea
rotation, crowded trades, same analysis the Insights tab shows, but as a
document you can email. Run it any time; it always reflects whatever is
currently in `data/data.json`.

```bash
python scripts/generate_summary_report.py --year 2025   # summarize a past year instead
```

---

## Hosting on GitHub Pages

1. Create a new repo and push this whole folder to it.
2. In the repo settings → Pages, set the source to the `main` branch, root folder.
3. GitHub will give you a URL like `https://yourname.github.io/repo-name/` —
   that's your live site. It updates automatically every time you push.

Because `index.html` embeds its data inline (rather than fetching a separate
JSON file at runtime), there are no CORS issues either way — it works
identically whether it's opened directly from disk or served from GitHub
Pages.

**Your monthly routine on GitHub becomes:**
```bash
git pull
python scripts/add_report.py new_report.csv
git add -A
git commit -m "Add July 2026 report"
git push
```

---

## Requirements

```bash
pip install -r requirements.txt
```

Only `openpyxl` (for reading `.xlsx` input files) and `python-docx` (for the
summary report generator) are needed. Everything else is the Python standard
library. No Node, no npm, no build tooling required to just view the site.

---

## Data notes & known corrections

A few things worth knowing about the underlying data, carried over from when
this was first assembled:

- **Analyst name merges.** The original source spreadsheet listed a handful
  of analysts under inconsistent names across different months (a stray
  sector-name prefix, a credential suffix that came and went, one month
  credited to a co-analyst). These were merged into one canonical identity
  per person, verified by unbroken ticker continuity across the switch. The
  mapping lives in `data/name_aliases.json` in case a future report repeats
  the inconsistency.
- **Five corrected data points.** Two HCI rows (Jun/Aug 2024), two ONTO rows
  (Oct/Nov 2024), and one XPO row (Dec 2024) had a PDF-extraction artifact —
  the price field was populated with a flat `500` alongside garbled
  boilerplate risk-disclosure text instead of a real company name. These are
  nulled out in `master_picks.csv` rather than guessed at.
- **Returns are computed from price, not trusted from any pre-built "return"
  column.** An earlier version of this dataset had a "return" column with
  legacy formula errors (thousands-of-percent swings on months where the
  price barely moved). `build_data.py` always derives return directly from
  `stock_price` at consecutive reports, which is more reliable.
- **A ticker switch attributes no return to the switch itself.** When an
  analyst's pick changes from month to month, there's no "exit price" for
  the abandoned position in this data, so that transition shows as a new
  pick with no return — not a zero, a genuine gap. All-time and trailing
  figures only compound the periods where a position was actually held.
