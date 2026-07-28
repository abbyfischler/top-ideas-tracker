# Oppenheimer Top Ideas — Analyst Coverage Tracker

A static, no-backend website that tracks every analyst's monthly stock pick
from Oppenheimer's "Top Ideas" reports, compounds their returns, and compares
them against a sector ETF (where available) and the S&P 500 (always).

The entire site is a handful of plain files (`index.html`, `css/`, `js/`,
`data/`) plus a small set of Python scripts that turn a new report PDF into
an updated site. No database, no server-side code, and no paid hosting is
required.

---

## Adding a new report — step by step

This is the one thing that needs to happen every month. Do this exactly the
same way each time, whether or not you're familiar with the rest of this
project.

### Every month, when a new Top Ideas report comes out:

1. Go to this repository on GitHub.
2. Open the **`incoming`** folder.
3. Click **Add file → Upload files**.
4. Drag the new month's Top Ideas PDF in, then click **Commit changes**.
5. Wait about a minute, then click the **Pull requests** tab at the top of
   the repository.
6. **If you see a Pull Request titled "New Top Ideas report(s) ready to
   merge"** — open it, glance at the summary, and click **Merge pull
   request**. The live site updates automatically within a minute or two.
   You're done.
7. **If instead there's no Pull Request, check the "Issues" tab.** An Issue
   there means the automation found something it wasn't confident about (a
   missing price date, an analyst it didn't recognize, a ticker it
   couldn't match) and needs a person to double-check before it goes live.
   The Issue will explain, in plain English, exactly what to look at. See
   **"If a report comes back with an Issue instead of a PR"** below for how
   to resolve it.

That's the whole workflow. No installing anything, no running code, no
touching a spreadsheet — just drop the PDF in and merge the Pull Request.

### One-time setup (do this once, the first time this repo is used)

Before the automation can open Pull Requests, GitHub Actions needs
permission to do so:

1. Go to **Settings → Actions → General** in this repository.
2. Scroll to **"Workflow permissions."**
3. Select **"Read and write permissions."**
4. Check **"Allow GitHub Actions to create pull requests."**
5. Save.

Without this one-time step, the automation can run but won't be able to
open the Pull Request or Issue it needs to.

### If a report comes back with an Issue instead of a Pull Request

This means the parser found something it wasn't sure about rather than
guessing — it's being careful with the data. The fix is usually quick:

- **"Could not find an explicit as-of date"** — open the PDF, find the
  actual date on the price table page near the back (titled "OPCO Top
  Ideas: Month Year"), and use that date when fixing the row.
- **"Known analyst had no pick found"** — check whether that analyst simply
  rotated off coverage that month (nothing to do), or whether the PDF's
  formatting changed unexpectedly (worth a closer look).
- **"Ticker matched but not found in the price table"** — usually means the
  ticker printed in the analyst's write-up doesn't exactly match the one in
  the back price table. Check the PDF for the correct symbol.

Once you know what needs fixing, download the CSV the parser already
produced (linked in the Issue, or regenerate it yourself with
`python scripts/parse_report_pdf.py the_report.pdf`), correct the one or two
fields by hand, and continue with the manual method below.

### Manual method (fallback, or for fixing a flagged report)

Use this if GitHub isn't available, or to fix a report that came back with
an Issue.

**1. Build a small CSV of that month's picks.**

Create a file (name it anything, e.g. `2026-07.csv`) with these columns:

| Column | Required? | Example | Notes |
|---|---|---|---|
| `report_key` | **yes** | `2026-07` | `YYYY-MM` — this is what makes reports sort chronologically. Use the report's *first* month if it spans two (e.g. "Jul-Aug 2026" → `2026-07`). |
| `report_label` | recommended | `Jul-Aug 2026` | Human-readable, shown in the UI. |
| `analyst` | **yes** | `Brian Schwartz` | Use the analyst's name as it appears in the report. If a report is inconsistent about it (this has happened before — sector-name prefixes, credential suffixes), add the mapping to `data/name_aliases.json` and it will be normalized automatically. |
| `company` | recommended | `Salesforce Inc.` | Shown in the pick history table. |
| `ticker` | **yes** | `CRM` | |
| `stock_price` | **yes** | `312.40` | The report's cover price for that pick. All the return math is built on this number. |
| `price_target` | optional | `380` | Shown in the detail table if present. |
| `price_as_of` | optional | `7/20/26` | M/D/YY. If the report doesn't print a specific date, leave it blank or use the report's disseminated date. |
| `rating` | optional | `O` | Not currently used anywhere in the UI. |

The fastest way to build this: open the new PDF, go through each analyst's
write-up (ticker, rating, price target), then cross-reference the price
table near the end of the report, which has the actual stock price and
report date for every ticker in one place.

A minimal CSV only needs `report_key`, `report_label`, `analyst`, `ticker`,
`stock_price` — everything else is optional.

**2. Run the update script.**

```bash
cd path/to/this/folder
python scripts/add_report.py 2026-07.csv
```

This will:
- normalize analyst names using `data/name_aliases.json`
- skip any row that's already in `master_picks.csv` for that report + analyst (safe to re-run)
- append the new rows to `data/master_picks.csv`
- regenerate `data/data.json`
- regenerate `index.html`

You'll see a summary of how many rows were added or skipped.

```bash
python scripts/add_report.py 2026-07.csv --dry-run     # preview only, writes nothing
python scripts/add_report.py 2026-07.csv --force        # overwrite existing rows for that month
python scripts/add_report.py 2026-07.xlsx --sheet "All Picks"   # xlsx input also works
```

**3. Check the output.**

Open `index.html` in a browser. The new month should appear immediately —
a new "latest pick" per analyst, updated returns, and a new period tab if
it's a new year. No further steps are needed for local viewing; if the site
is hosted on GitHub Pages, commit and push the updated files to publish it.

**4. If a new analyst shows up.**

`build_data.py` prints a warning listing any analyst it doesn't recognize
from `data/sector_map.json`. Add two entries to classify them:

```jsonc
// data/sector_map.json
{
  "group": { "...": "...", "New Analyst Name": "TECHNOLOGY" },
  "label": { "...": "...", "New Analyst Name": "Coverage Area Name" }
}
```

Valid `"group"` values: `TECHNOLOGY`, `HEALTH CARE`, `INDUSTRIALS/ENERGY`,
`FINANCIALS/CONSUMER`. Then re-run
`python scripts/build_data.py && python scripts/build_site.py` (or just
re-run `add_report.py`, which does both automatically).

**5. If you get sector ETF data for an analyst who doesn't have one yet.**

Add an entry to `data/etf_map.json`:

```jsonc
{
  "Analyst Name": {"etf": "XLK", "label": "Coverage area name", "r": [2023_return, 2024_return, 2025_return, 2026_return]}
}
```

Use `null` for any year without a number (e.g. `[58.47, 23.4, null, null]`).
Every analyst is already compared to the S&P 500 automatically — this adds
a more specific sector-level comparison on top.

**6. Updating the S&P 500 benchmark.**

`data/spx_benchmark.json` holds full-year S&P 500 returns for prior years
and a year-to-date figure for the current year. Update the current year's
number periodically (e.g. each quarter, or whenever a report is added) so
the comparison stays current — it will not update itself.

---

## Hosting on GitHub Pages

1. Push this whole folder to a GitHub repository (or use this one).
2. In the repository settings, go to **Pages**, and set the source to the
   `main` branch, root folder.
3. GitHub provides a URL in the form
   `https://<organization-or-username>.github.io/<repo-name>/` — that's the
   live site. It updates automatically every time changes are pushed
   (including automatically, whenever a Pull Request from the monthly
   automation above is merged).

Because `index.html` embeds its data inline (rather than fetching a
separate JSON file at runtime), there are no CORS issues either way — it
works identically whether it's opened directly from disk or served from
GitHub Pages.

---

## Viewing the site locally

**Simplest option:** double-click `index.html`, or open it in a browser
using **File → Open**. Because the data is embedded directly in the HTML
file rather than fetched separately, this works with no server, no
internet connection, and no setup — you'll see exactly what the live site
shows.

Two things to keep in mind:

- `index.html` links out to `css/style.css` and `js/script.js`, so **those
  two folders need to stay right next to it.** If only the single
  `index.html` file is copied or emailed by itself, the page will still
  load but with no styling (raw unstyled text, and a large unstyled circle
  where the logo should be — that's this exact issue).
- To get one file that can be renamed, moved, or emailed around with zero
  risk of that happening, run `python scripts/build_standalone.py`. It
  inlines everything — CSS, JavaScript, and data — into a single
  self-contained file (`standalone.html` by default). Slightly larger, but
  foolproof.

**Optional: running a local web server.** This isn't required for normal
viewing, but is occasionally useful when testing changes to the JavaScript
(some browsers restrict certain features when a page is opened directly
from disk via `file://`). From this folder, run:

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000` in a browser. Press Ctrl+C in the
terminal to stop the server when finished.

---

## What's in this folder

```
├── index.html               ← the website itself. Open this to view the tracker.
├── css/style.css             ← all styling
├── js/script.js              ← all interactivity (filtering, sorting, charts, insights)
├── templates/
│   └── index_template.html   ← skeleton index.html is generated from (has a __DATA_JSON__ placeholder)
├── incoming/                 ← drop new report PDFs here — see "Adding a new report" above
│   └── processed/            ← PDFs land here automatically once they've been processed
├── .github/workflows/
│   └── process-report.yml    ← the GitHub Actions automation that runs when a PDF is dropped in incoming/
├── data/
│   ├── master_picks.csv      ← THE SOURCE OF TRUTH. One row per analyst pick per report.
│   ├── sector_map.json       ← analyst → sector group + coverage-area label
│   ├── etf_map.json          ← analyst → sector ETF ticker + annual returns (partial coverage)
│   ├── spx_benchmark.json    ← S&P 500 annual returns (universal benchmark, all analysts)
│   ├── russell_benchmark.json ← Russell index annual returns (secondary benchmark)
│   ├── exit_prices.csv       ← generated from exit_prices_needed.xlsx — see "Filling in exit prices" below
│   ├── name_aliases.json     ← known analyst-name inconsistencies → canonical name
│   └── data.json             ← GENERATED — what index.html actually loads. Don't hand-edit this.
├── scripts/
│   ├── build_data.py         ← master_picks.csv + maps → data/data.json
│   ├── build_site.py         ← data/data.json + template → index.html (linked css/js)
│   ├── build_standalone.py   ← data/data.json + template → one self-contained .html file
│   ├── parse_report_pdf.py   ← reads a new report PDF directly, no manual transcription needed
│   ├── add_report.py         ← appends parsed/manual picks to master_picks.csv and rebuilds everything
│   ├── apply_exit_prices.py  ← ingests a Bloomberg-filled exit_prices_needed.xlsx into data/exit_prices.csv
│   └── generate_summary_report.py ← makes a Word doc summary of performance
├── exit_prices_needed.xlsx   ← lists every ticker-switch missing a return — see "Filling in exit prices" below
└── requirements.txt
```

**Day-to-day maintenance never requires touching `index.html`, `css/`,
`js/`, or `data/data.json` directly.** The one file that matters for a
routine monthly update is `data/master_picks.csv`, and the one script that
needs to be run is `add_report.py` — both are handled automatically by the
GitHub Pull Request workflow above.

---

## For maintainers: how the code works

Everything below is for anyone who needs to modify this project, debug an
issue, or understand the data pipeline — not required for routine monthly
updates.

### Data flow, end to end

```
Report PDF
   │
   ▼  (parse_report_pdf.py — text pattern matching, no AI)
CSV of that month's picks
   │
   ▼  (add_report.py)
data/master_picks.csv   ← the single source of truth, one row per analyst per report
   │
   ▼  (build_data.py)
data/data.json          ← computed returns, cumulative series, benchmarks
   │
   ▼  (build_site.py)
index.html              ← data.json injected into templates/index_template.html
```

`add_report.py` is a convenience wrapper: it normalizes the new rows,
appends them to `master_picks.csv`, then calls `build_data.py` and
`build_site.py` automatically so the site is always in sync after one
command. Running the two build scripts directly is only necessary if
`data/master_picks.csv` (or one of the JSON reference files below) was
edited by hand.

### The reference files `build_data.py` reads, besides `master_picks.csv`

- **`data/sector_map.json`** — maps each analyst to a sector group
  (`TECHNOLOGY`, `HEALTH CARE`, `INDUSTRIALS/ENERGY`, `FINANCIALS/CONSUMER`)
  and a human-readable coverage-area label. Used to organize the site into
  sector tabs.
- **`data/etf_map.json`** — for analysts where a relevant sector ETF has
  been identified, maps the analyst to that ETF's ticker and its annual
  returns, so their performance can be compared against something more
  specific than the S&P 500. Coverage is partial by design — not every
  analyst has a clean single-ETF proxy for their coverage area.
- **`data/spx_benchmark.json`** and **`data/russell_benchmark.json`** —
  annual index returns used as universal benchmarks for every analyst,
  regardless of whether they have a sector ETF.
- **`data/name_aliases.json`** — maps inconsistent name variants (a stray
  sector prefix, a credential suffix that came and went, one month
  credited to a co-analyst) to one canonical name, so the same person's
  picks stay grouped together across reports.
- **`data/exit_prices.csv`** — generated by `apply_exit_prices.py` (see
  below); supplies the exit price for ticker switches so a real return can
  be computed for the month a position was abandoned.

### How returns are computed

`build_data.py` groups every row in `master_picks.csv` by analyst, sorts
each analyst's picks chronologically by `report_key`, and for each
consecutive pair of reports computes the return as the percentage change in
`stock_price`. This is deliberately *not* trusted from any pre-built
"return" column in the source data — an earlier version of this dataset
had a return column with legacy formula errors, so returns are always
derived directly from price.

- If the ticker is unchanged between two consecutive reports, that's a
  **held** return: the plain price change.
- If the ticker changes, that's an **exit**: no return is attributed to the
  transition itself unless an exit price has been supplied via
  `data/exit_prices.csv` (see "Filling in exit prices" below) — otherwise
  it shows as a gap, not a zero.
- Per-analyst cumulative return series, calendar-year returns, and
  trailing-12-report returns are all built by compounding these
  period-over-period returns in sequence.

### The PDF automation (`parse_report_pdf.py` and the GitHub Action)

Oppenheimer's report has the same two-part structure every month: analyst
write-ups (name, ticker, rating, price target) followed by a price table
near the back with the as-of stock price for every ticker. `parse_report_pdf.py`
matches each name from a known-analyst list against the write-up section,
extracts the ticker and price target, then looks up that ticker's real
price in the back table.

This is plain text pattern matching — **no AI or LLM is involved** — so it
behaves identically every time, including inside a GitHub Action with no
external API access. It's intentionally conservative: if a known analyst
can't be matched to a pick, or a matched ticker isn't found in the price
table, that row is flagged rather than guessed at, and the script exits
non-zero. That non-zero exit is what makes `.github/workflows/process-report.yml`
open a GitHub Issue for a human to check, instead of silently pushing bad
data to the live site. When parsing succeeds cleanly, the same workflow
calls `add_report.py` and opens a Pull Request with the update instead.

### Generating a summary report to send around

```bash
python scripts/generate_summary_report.py
```

Produces a Word document (`.docx`) summarizing the current year's
performance — top/bottom performers, sector scoreboard, idea rotation,
crowded trades — mirroring the analysis in the site's Insights tab, but as
a document that can be emailed. It always reflects whatever is currently in
`data/data.json`.

```bash
python scripts/generate_summary_report.py --year 2025   # summarize a past year instead
python scripts/generate_summary_report.py --year ALL     # summarize the full tracked history
```

---

## Hosting on a company server instead of GitHub

Everything here is a handful of static files (`index.html`, `css/`, `js/`,
`data/`) — any web server that can serve a plain HTML file can host this.
There's nothing GitHub-specific about the site itself; GitHub Pages is just
one convenient way to serve static files for free. GitHub *Actions* (the
PDF automation) is the one piece that's specific to GitHub — the
equivalent for a company server is `scripts/watch_incoming.py`, included in
this folder for exactly that purpose.

**To move this to a company server:**

1. Copy this entire folder to wherever the server serves files from (e.g.
   `/var/www/top-ideas/` on Linux, or the equivalent for your setup).
   Whatever currently points at the internal site should point at this
   folder's `index.html`.
2. Make sure Python 3 is available on that server (`python3 --version`).
   Most Linux servers already have it; if not, IT can install it in a few
   minutes.
3. Install the two Python packages this needs:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up a recurring job to run the watcher — this is what replaces
   GitHub Actions:
   ```bash
   crontab -e
   ```
   then add this line (runs every 10 minutes):
   ```
   */10 * * * * cd /var/www/top-ideas && python3 scripts/watch_incoming.py >> logs/watch.log 2>&1
   ```
   (On Windows, use Task Scheduler instead — create a task that runs
   `python.exe scripts\watch_incoming.py` every 10 minutes, with "Start in"
   set to this folder.)
5. From here on, dropping a PDF into this folder's `incoming/` subfolder
   (via whatever mechanism is already in place — network share, SFTP,
   etc.) gets picked up within 10 minutes, and `index.html` updates in
   place automatically.

**The difference from the GitHub version:** there's no Pull Request review
step by default — a cleanly-parsed report goes live automatically. Reports
the parser isn't confident about get moved to `incoming/needs_review/`
with a `..._WHAT_TO_CHECK.txt` file explaining what to look at, and nothing
touches the live site until that's resolved. A human-approval step can be
added (e.g. writing to a staging copy instead of the live `index.html`
until someone confirms) with a small modification to `watch_incoming.py`.

**Running it manually**, instead of waiting for the schedule:
```bash
python scripts/watch_incoming.py
```

---

## Filling in exit prices for ticker switches (optional, improves accuracy)

When an analyst switches from one ticker to another, that month shows a
blank return by default — there's no way to know what the abandoned
position was worth on the day it was dropped, since the monthly reports
only ever list the price of the *current* pick.

With access to a market data terminal (Bloomberg, FactSet, etc.), this gap
can be filled in to get a real return for every switch, which also makes
each analyst's all-time and yearly totals more accurate (they may go up or
down — a switch made because a position was falling will lower the total,
not raise it).

1. Open **`exit_prices_needed.xlsx`** — it lists every ticker-switch in the
   dataset, grouped by ticker, with the exact date needed for each. The
   "Instructions" tab explains the Bloomberg side of it (pull up `HP <GO>`
   for each ticker, fill in the closing price for each listed date).
2. Once it's filled in, run:
   ```bash
   python scripts/apply_exit_prices.py exit_prices_needed.xlsx
   ```
   (add `--allow-partial` if only some of it was completed, to apply
   whatever's done so far)
3. Then rebuild:
   ```bash
   python scripts/build_data.py
   python scripts/build_site.py
   ```

This is entirely optional and can be done incrementally — filling in a
handful of tickers today and the rest later works fine, since each run
just applies whatever's currently filled in. Rows with a filled-in exit
price show a small "exit: TICKER" tag next to the return in that analyst's
detail view, so it's always clear which position a given return describes.

---

## Requirements

```bash
pip install -r requirements.txt
```

Only `openpyxl` (for reading `.xlsx` input files) and `python-docx` (for
the summary report generator) are needed. Everything else is the Python
standard library. No Node, no npm, no build tooling required to just view
the site.

**To run `scripts/parse_report_pdf.py` locally** (rather than letting the
GitHub Action do it), `pdftotext` is also needed, from the `poppler`
package:
```bash
brew install poppler        # macOS
sudo apt install poppler-utils   # Linux
```
This isn't needed for the standard GitHub workflow above — the GitHub
Action installs it automatically in its own environment.

---

## Data quality notes & known corrections

A few things worth knowing about the underlying data, carried over from
when this tracker was first assembled:

- **Analyst name merges.** The original source spreadsheet listed a
  handful of analysts under inconsistent names across different months (a
  stray sector-name prefix, a credential suffix that came and went, one
  month credited to a co-analyst). These were merged into one canonical
  identity per person, verified by unbroken ticker continuity across the
  switch. The mapping lives in `data/name_aliases.json` in case a future
  report repeats the inconsistency.
- **Five corrected data points.** Two HCI rows (Jun/Aug 2024), two ONTO
  rows (Oct/Nov 2024), and one XPO row (Dec 2024) had a PDF-extraction
  artifact — the price field was populated with a flat `500` alongside
  garbled boilerplate risk-disclosure text instead of a real company name.
  These are nulled out in `master_picks.csv` rather than guessed at.
- **Returns are computed from price, not trusted from any pre-built
  "return" column.** An earlier version of this dataset had a "return"
  column with legacy formula errors (thousands-of-percent swings on months
  where the price barely moved). `build_data.py` always derives return
  directly from `stock_price` at consecutive reports, which is more
  reliable.
- **A ticker switch attributes no return to the switch itself** unless an
  exit price has been supplied (see "Filling in exit prices" above). When
  an analyst's pick changes from month to month, there's no exit price for
  the abandoned position in the base dataset, so that transition shows as
  a new pick with no return — not a zero, a genuine gap. All-time and
  trailing figures only compound the periods where a position was actually
  held.
- **Stock splits are not detected or adjusted for automatically.** Each
  report's `stock_price` is taken exactly as printed in that month's PDF.
  If a company splits its stock between two reports, the raw price will
  show a large jump or drop that doesn't reflect an actual gain or loss —
  this has been checked and corrected by hand for known cases in
  `master_picks.csv`, particularly among semiconductor names, where this
  came up during a Bloomberg cross-check of the data. When adding a new
  report, if a month-over-month price move looks far larger than what the
  analyst's own commentary would suggest, check whether the company did a
  stock split around that date before entering the price — if so, use the
  split-adjusted price so the return calculation stays accurate, and note
  the correction here.
