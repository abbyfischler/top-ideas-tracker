# Adding a New Monthly Report — Quick Guide

This is the only thing you need to do each month. Everything else happens automatically.

## If the site is on GitHub

1. Go to the repository's page on GitHub
2. Click into the **`incoming`** folder
3. Click **Add file → Upload files**
4. Drag the new month's Top Ideas PDF in, then click **Commit changes**
5. Wait about a minute, then click the **Pull requests** tab at the top

**If you see a Pull Request titled "New Top Ideas report(s) ready to merge"**
— open it, glance at the summary, and click **Merge pull request**. The live
site updates within a minute or two. Done.

**If instead you see nothing in Pull Requests, check the "Issues" tab.** An
Issue there means the automation found something it wasn't sure about (a
missing date, an analyst it didn't recognize, etc.) and needs a person to
take a quick look before it goes live — the Issue will explain exactly what
to check, in plain English. This is by design: it's being careful with your
data rather than guessing.

## If the site is on the company server (not GitHub)

Same idea, simpler:

1. Drop the new PDF into the `incoming` folder on the server (however you
   normally move files there — network drive, SFTP, etc.)
2. Within about 10 minutes, it'll be processed automatically
3. Check the `incoming/processed` folder — if the PDF is there, it worked
4. If it's in `incoming/needs_review` instead, open the matching
   `..._WHAT_TO_CHECK.txt` file next to it — it explains what needs a look

No merging or approving anything — on the company server there's no Pull
Request step, it just updates the live site directly once it's confident
the data is clean. (If you want a review step added here too, ask whoever
manages the server — it's a small change.)

## Either way

You never need to open the spreadsheet, run any code, or use Claude for
this. Just the PDF, dropped in one folder.
