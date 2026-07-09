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

**Just here to add a monthly report and nothing else?** Skip this whole file
and read **`BOSS_QUICKSTART.md`** instead — it's one page, no technical
background needed.

---

## What's in this folder

```
├── BOSS_QUICKSTART.md      ← one-page, non-technical: how to add a monthly report
├── index.html              ← the actual website. Open this.
├── css/style.css           ← all styling
├── js/script.js            ← all interactivity (filtering, sorting, charts, insights)
├── templates/
│   └── index_template.html ← skeleton index.html is generated from (has a __DATA_JSON__ placeholder)
├── incoming/                ← drop new report PDFs here — see "Adding next month's report" below
│   └── processed/           ← PDFs land here automatically once they've been processed
├── .github/workflows/
│   └── process-report.yml   ← the automation that runs when a PDF is dropped in incoming/
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
│   ├── parse_report_pdf.py ← reads a new report PDF directly, no manual transcription needed
│   ├── add_report.py       ← appends parsed/manual picks to master_picks.csv and rebuilds everything
│   ├── apply_exit_prices.py ← ingests a Bloomberg-filled exit_prices_needed.xlsx into data/exit_prices.csv
│   └── generate_summary_report.py ← makes a Word doc summary you can send around
└── requirements.txt
```

`exit_prices_needed.xlsx` (in the root) lists every ticker-switch that's
currently missing a return — see "Filling in exit prices" below.

**You should basically never need to touch `index.html`, `css/`, `js/`, or
`data/data.json` directly.** The one file that matters is
`data/master_picks.csv`, and the one script you run is `add_report.py`.

---

## Adding next month's report

There are two ways to do this. **Use the first one** — it needs nothing
installed and works entirely through GitHub's website, which matters if
whoever's doing this monthly doesn't have Python, git, or Claude access.

### Option A: Drop the PDF in (fully automatic, no software needed)

**One-time setup** (do this once, right after uploading the repo): go to
**Settings → Actions → General**, scroll to "Workflow permissions", select
**"Read and write permissions"**, and check **"Allow GitHub Actions to
create pull requests"**. Without this, the automation can't open the Pull
Request or Issue it needs to.

Then, every month:

1. Go to the repo on GitHub, open the **`incoming`** folder
2. Click **Add file → Upload files**, drag the new month's PDF in, commit
3. Wait a minute or two, then check the repo's **Pull requests** tab

That's it. Behind the scenes, a GitHub Action automatically:
- reads every analyst's pick and price straight out of the PDF text
- checks it against the known analyst roster and the report's own price table
- if everything checks out, opens a **Pull Request** with the update ready to merge — just click **Merge pull request** and the live site updates within a minute or two
- if anything looks off (a missing price date, an analyst it couldn't find a pick for, etc.), it opens an **Issue** instead explaining exactly what to check, and leaves the site untouched until that's resolved

This uses plain text pattern-matching against Oppenheimer's report format — no AI involved, so it works the same way every time and doesn't need anyone signed into anything. It's deliberately cautious: if it isn't confident about a row, it asks a human rather than guessing.

**If a report ever comes back with an Issue instead of a PR**, the fix is
usually quick:
- *"Could not find an explicit as-of date"* — open the PDF, find the actual date on the price table page (near the back, titled "OPCO Top Ideas: Month Year"), and note it for whoever fixes the CSV (see Option B)
- *"Known analyst had no pick found"* — check if they simply rotated off coverage that month (nothing to do) or if the PDF's formatting changed unexpectedly (worth a look)
- *"Ticker matched but not found in the price table"* — usually means the ticker symbol printed in the write-up doesn't exactly match the one in the back table; check the PDF

Once you know what needs fixing, the easiest path is usually to download the
CSV the parser already produced (linked in the Issue, or regenerate it with
`python scripts/parse_report_pdf.py the_report.pdf`), fix the one or two
fields by hand, and continue with Option B below.

### Option B: Manual CSV (fallback, or for fixing a flagged report)

#### 1. Build a small CSV of that month's picks

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

#### 2. Run the update script

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

#### 3. Check the output

Open `index.html` — the new month should show up immediately (new "latest
pick" per analyst, updated returns, new period tab if it's a new year, etc.)
No further steps needed for local viewing.

#### 4. If a new analyst shows up

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

#### 5. If you get sector ETF data for an analyst who doesn't have one yet

Add an entry to `data/etf_map.json`:

```jsonc
{
  "Analyst Name": {"etf": "XLK", "label": "Coverage area name", "r": [2023_return, 2024_return, 2025_return, 2026_return]}
}
```

Use `null` for any year you don't have a number for (e.g. `[58.47, 23.4, null, null]`).
Every analyst already gets compared to the S&P 500 automatically — this just
adds a more specific sector-level comparison on top.

#### 6. Updating the S&P 500 benchmark

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

Monthly updates happen through Option A above (drop a PDF in `incoming/`,
merge the PR it opens) — see **BOSS_QUICKSTART.md** for the short version to
hand off to whoever's doing this monthly.

---

## Hosting on your own company server instead of GitHub

Everything here is a handful of static files (`index.html`, `css/`, `js/`,
`data/`) — any web server that can serve a plain HTML file can host this.
There's nothing GitHub-specific about the site itself; GitHub Pages is just
one convenient way to serve static files for free. GitHub *Actions*
(the PDF automation) is the one piece that's specific to GitHub — the
company-server equivalent is `scripts/watch_incoming.py`, included in this
folder for exactly that purpose.

**To move this to a company server:**

1. Copy this entire folder to wherever the server serves files from (e.g.
   `/var/www/top-ideas/` on Linux, or the equivalent on your setup). Whatever
   currently points people at your internal site should point at this
   folder's `index.html`.
2. Make sure Python 3 is available on that server (`python3 --version`).
   Most Linux servers have it already; if not, your IT team can install it
   in a few minutes.
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
   set to this folder. Ask your IT team if you're not sure how — it's a
   5-minute setup for them.)
5. That's it. From here on, dropping a PDF into this folder's `incoming/`
   subfolder (via however your team normally puts files on that server —
   a network share, SFTP, whatever's already in place) gets picked up
   within 10 minutes, and `index.html` updates in place automatically.

**The difference from the GitHub version:** there's no Pull Request review
step here by default — a cleanly-parsed report goes live automatically.
Reports the parser isn't confident about get moved to
`incoming/needs_review/` with a `..._WHAT_TO_CHECK.txt` file explaining what
to look at, and nothing touches the live site until that's resolved. If you
want a human-approval step added even for the clean case, that's a small
modification to `watch_incoming.py` (e.g. writing to a staging copy instead
of the live `index.html` until someone confirms) — ask whoever manages the
server to wire that up if it's worth the extra step for your team.

**You can also run it manually** any time, instead of waiting for the
schedule:
```bash
python scripts/watch_incoming.py
```

---

## Filling in exit prices for ticker switches (optional, improves accuracy)

When an analyst switches from one ticker to another, that month shows a
blank return by default — there's no way to know what the abandoned
position was worth on the day it was dropped, since the monthly reports
only ever list the price of the *current* pick.

If you have access to a market data terminal (Bloomberg, FactSet, etc.),
you can fill this gap in and get a real return for every switch, which
also makes each analyst's all-time and yearly totals more accurate (they
may go up or down — a switch made because a position was falling will
lower the total, not raise it).

1. Open **`exit_prices_needed.xlsx`** — it lists every ticker-switch in the
   dataset (currently 377), grouped by ticker, with the exact date needed
   for each. The "Instructions" tab in that file explains the Bloomberg
   side of it (pull up `HP <GO>` for each ticker, fill in the closing
   price for each listed date).
2. Once it's filled in, run:
   ```bash
   python scripts/apply_exit_prices.py exit_prices_needed.xlsx
   ```
   (add `--allow-partial` if you only got through some of it and want to
   apply what's done so far)
3. Then rebuild as usual:
   ```bash
   python scripts/build_data.py
   python scripts/build_site.py
   ```

This is entirely optional and can be done incrementally — filling in 20
tickers today and the rest next week works fine, each run just applies
whatever's currently filled in. Rows with a filled-in exit price show a
small "exit: TICKER" tag next to the return in that analyst's detail view,
so it's always clear which position a given return describes.

---

## Requirements

```bash
pip install -r requirements.txt
```

Only `openpyxl` (for reading `.xlsx` input files) and `python-docx` (for the
summary report generator) are needed. Everything else is the Python standard
library. No Node, no npm, no build tooling required to just view the site.

**If you want to run `scripts/parse_report_pdf.py` locally** (rather than
letting the GitHub Action do it), you'll also need `pdftotext`, which comes
from the `poppler` package:
```bash
brew install poppler        # macOS
sudo apt install poppler-utils   # Linux
```
This isn't needed for Option A above — the GitHub Action installs it
automatically in its own environment.

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
