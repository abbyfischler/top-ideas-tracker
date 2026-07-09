Drop a new month's Top Ideas PDF here (just the PDF file, nothing else needed)
and GitHub will automatically:

1. Read every analyst's pick and price straight out of the PDF
2. Add it to the tracker's data
3. Either open a Pull Request ready to merge (if everything parsed cleanly),
   or open an Issue explaining exactly what needs a quick manual check (if
   something looked off — a missing date, an analyst it didn't recognize,
   etc.)

You don't need git, a terminal, or anything installed — uploading the file
through GitHub's website ("Add file" → "Upload files" → drag it in here) is
enough to kick this off.

Once a PDF has been processed, it gets moved into `incoming/processed/`
automatically so this folder stays clean for the next one.

See the main README.md for the full explanation of what's happening behind
the scenes.
