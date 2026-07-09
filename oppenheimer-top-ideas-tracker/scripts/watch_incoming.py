#!/usr/bin/env python3
"""
watch_incoming.py — The company-server equivalent of the GitHub Action.

Run this on a schedule (cron, Windows Task Scheduler, etc.) on any server
that can run Python. It watches the incoming/ folder for new PDFs and does
exactly what the GitHub Action does — no GitHub involved at all:

    1. Parses each new PDF (scripts/parse_report_pdf.py)
    2. If it parses cleanly: adds it to the tracker (scripts/add_report.py),
       which rebuilds data/data.json and index.html, and moves the PDF to
       incoming/processed/
    3. If anything looks uncertain: moves the PDF to incoming/needs_review/
       instead, and writes a .txt file right next to it explaining exactly
       what to check — nothing gets added to the live site until that's
       resolved.

Because index.html sits right in this same folder, whatever web server is
already serving this folder (Apache, Nginx, IIS, an S3 bucket synced on a
schedule, whatever your IT team uses) will pick up the update automatically
— there's no separate "deploy" step.

SETUP (run once)
    Add this to run every 10 minutes via cron (Linux/Mac):
        crontab -e
        */10 * * * * cd /path/to/this/folder && python3 scripts/watch_incoming.py >> logs/watch.log 2>&1

    Or via Windows Task Scheduler: create a task that runs
        python.exe C:/path/to/this/folder/scripts/watch_incoming.py
    every 10 minutes, with "Start in" set to this folder.

USAGE (manual, if you'd rather just run it by hand after adding a PDF)
    python scripts/watch_incoming.py
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INCOMING = ROOT / "incoming"
PROCESSED = INCOMING / "processed"
NEEDS_REVIEW = INCOMING / "needs_review"
LOGS = ROOT / "logs"


def log(msg):
    LOGS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line)
    with open(LOGS / "watch.log", "a") as f:
        f.write(line + "\n")


def main():
    PROCESSED.mkdir(exist_ok=True)
    NEEDS_REVIEW.mkdir(exist_ok=True)

    pdfs = sorted(INCOMING.glob("*.pdf"))
    if not pdfs:
        log("No new PDFs in incoming/. Nothing to do.")
        return

    for pdf in pdfs:
        log(f"Found new report: {pdf.name}")
        csv_path = ROOT / f"_tmp_{pdf.stem}.csv"

        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "parse_report_pdf.py"), str(pdf), "--out", str(csv_path)],
            capture_output=True, text=True
        )
        output = result.stdout + result.stderr
        print(output)

        if result.returncode != 0:
            dest = NEEDS_REVIEW / pdf.name
            pdf.rename(dest)
            note_path = NEEDS_REVIEW / f"{pdf.stem}_WHAT_TO_CHECK.txt"
            note_path.write_text(
                f"This report couldn't be fully auto-processed on {datetime.now().strftime('%Y-%m-%d %H:%M')}.\n\n"
                f"{output}\n\n"
                f"What to do:\n"
                f"1. Open the CSV this run produced (if it got that far): {csv_path if csv_path.exists() else '(not created — see warnings above)'}\n"
                f"2. Fix whatever's flagged above\n"
                f"3. Run: python scripts/add_report.py <the fixed csv>\n"
                f"4. Delete this folder's copy of the PDF once it's handled (or leave it, it won't be re-processed automatically)\n"
            )
            log(f"NEEDS REVIEW — moved to {dest}, see {note_path.name}")
            continue

        add_result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "add_report.py"), str(csv_path)],
            capture_output=True, text=True
        )
        print(add_result.stdout + add_result.stderr)
        if add_result.returncode != 0:
            log(f"ERROR running add_report.py for {pdf.name} — left in place, check logs above")
            continue

        dest = PROCESSED / pdf.name
        pdf.rename(dest)
        csv_path.unlink(missing_ok=True)
        log(f"SUCCESS — {pdf.name} added to the tracker, site rebuilt, moved to {dest}")


if __name__ == "__main__":
    main()
