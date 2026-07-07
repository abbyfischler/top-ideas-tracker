#!/usr/bin/env python3
"""
generate_summary_report.py — Generate a Word doc summary of analyst
performance from data/data.json. Mirrors the Insights tab's analysis
(top/bottom performers, sector scoreboard, idea rotation, crowded trades)
as a document you can send around.

Usage:
    python scripts/generate_summary_report.py                # summarizes the latest year with data
    python scripts/generate_summary_report.py --year 2026     # summarize a specific year
    python scripts/generate_summary_report.py --year ALL      # summarize the full tracked history
    python scripts/generate_summary_report.py --out my_report.docx
"""
import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = Path(__file__).resolve().parent.parent
SECTOR_ORDER = ['TECHNOLOGY', 'HEALTH CARE', 'INDUSTRIALS/ENERGY', 'FINANCIALS/CONSUMER']
SECTOR_LABELS = {
    'TECHNOLOGY': 'Technology',
    'HEALTH CARE': 'Health Care',
    'INDUSTRIALS/ENERGY': 'Industrials & Energy',
    'FINANCIALS/CONSUMER': 'Financials & Consumer',
}

BRASS = RGBColor(0xB4, 0x82, 0x2E)
POS = RGBColor(0x1E, 0x7A, 0x4E)
NEG = RGBColor(0xA8, 0x2E, 0x24)
DIM = RGBColor(0x55, 0x55, 0x55)


def compound_return(entries):
    cum, any_ret = 1.0, False
    for h in entries:
        if h.get('return') is not None:
            cum *= (1 + h['return'])
            any_ret = True
    return round((cum - 1) * 100, 1) if any_ret else None


def churn_rate(entries):
    if not entries:
        return None
    switches = sum(1 for h in entries if h.get('new_pick'))
    return switches / len(entries)


def slice_for_period(history, period):
    if period == 'ALL':
        return history
    return [h for h in history if h.get('report_key', '').startswith(period)]


def short_name(analyst):
    return analyst.split(',')[0].split(' ')[-1]


def fmt_pct(v):
    if v is None:
        return "—"
    sign = '+' if v >= 0 else ''
    return f"{sign}{v:.1f}%"


def shade_cell(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)


def set_col_widths(table, widths):
    table.autofit = False
    for row in table.rows:
        for cell, w in zip(row.cells, widths):
            cell.width = w


def add_heading(doc, text, size=15, color=BRASS, space_before=18, space_after=8):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(size)
    run.font.color.rgb = color
    return p


def pct_run(paragraph, value, bold=True):
    run = paragraph.add_run(fmt_pct(value))
    run.bold = bold
    run.font.color.rgb = POS if (value is not None and value >= 0) else (NEG if value is not None else DIM)
    return run


def build_analysis(data, period):
    pool = []
    for a in data:
        hist = slice_for_period(a['history'], period)
        if not hist:
            continue
        ret = compound_return(hist) if period != 'ALL' else a['total_return']
        pool.append({
            'analyst': a['analyst'],
            'sector_group': a['sector_group'],
            'sector_label': a['sector_label'],
            'history': hist,
            'ret': ret,
            'churn': churn_rate(hist),
            'n': len(hist),
        })

    with_ret = [a for a in pool if a['ret'] is not None]
    ranked = sorted(with_ret, key=lambda a: -a['ret'])
    top5 = ranked[:5]
    bottom5 = list(reversed(ranked[-5:])) if len(ranked) >= 1 else []

    sector_stats = []
    for sec in SECTOR_ORDER:
        grp = [a for a in with_ret if a['sector_group'] == sec]
        if not grp:
            continue
        avg = sum(a['ret'] for a in grp) / len(grp)
        sector_stats.append({'sec': sec, 'avg': avg, 'n': len(grp)})
    sector_stats.sort(key=lambda s: -s['avg'])

    churn_pool = [a for a in pool if a['n'] >= 3 and a['churn'] is not None]
    rotators = sorted(churn_pool, key=lambda a: -a['churn'])[:5]
    loyalists = sorted(churn_pool, key=lambda a: a['churn'])[:5]

    ticker_map = defaultdict(set)
    for a in pool:
        for h in a['history']:
            if h.get('ticker'):
                ticker_map[h['ticker']].add(a['analyst'])
    crowded = sorted(
        [(t, sorted(s)) for t, s in ticker_map.items() if len(s) >= 2],
        key=lambda x: -len(x[1])
    )[:10]

    avg_all = sum(a['ret'] for a in with_ret) / len(with_ret) if with_ret else None

    return {
        'pool': pool, 'with_ret': with_ret, 'top5': top5, 'bottom5': bottom5,
        'sector_stats': sector_stats, 'rotators': rotators, 'loyalists': loyalists,
        'crowded': crowded, 'avg_all': avg_all,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--year', default=None, help='Year to summarize (e.g. 2026), or ALL for full history. Defaults to the latest year with data.')
    ap.add_argument('--out', default=None, help='Output .docx filename')
    args = ap.parse_args()

    data = json.loads((ROOT / 'data' / 'data.json').read_text())

    if args.year:
        period = args.year
    else:
        years = set()
        for a in data:
            for h in a['history']:
                if h.get('report_key'):
                    years.add(h['report_key'][:4])
        period = max(years) if years else 'ALL'

    period_label = 'the full tracked history (Jan 2023 \u2013 present)' if period == 'ALL' else period
    analysis = build_analysis(data, period)

    out_name = args.out or f"top_ideas_summary_{period}.docx"
    out_path = ROOT / out_name

    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.left_margin = section.right_margin = Inches(0.9)
    section.top_margin = section.bottom_margin = Inches(0.8)

    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(10.5)

    # Title
    title = doc.add_paragraph()
    title.paragraph_format.space_after = Pt(2)
    r = title.add_run("Top Ideas — Coverage Summary")
    r.bold = True
    r.font.size = Pt(22)
    r.font.color.rgb = RGBColor(0x1a, 0x1a, 0x1a)

    sub = doc.add_paragraph()
    sub.paragraph_format.space_after = Pt(2)
    r = sub.add_run(f"Period: {period_label}")
    r.font.size = Pt(12)
    r.font.color.rgb = BRASS
    r.bold = True

    meta = doc.add_paragraph()
    meta.paragraph_format.space_after = Pt(16)
    r = meta.add_run(f"Generated {date.today().strftime('%B %d, %Y')} \u00b7 Oppenheimer & Co. Top Ideas Monthly, analyst coverage tracker")
    r.font.size = Pt(9)
    r.font.color.rgb = DIM
    r.italic = True

    # ---- Overview narrative ----
    add_heading(doc, "Overview")
    n_analysts = len(analysis['with_ret'])
    p = doc.add_paragraph()
    p.add_run(f"Across {n_analysts} analysts with a computable return in {period_label}, the average pick moved ")
    pct_run(p, analysis['avg_all'])
    p.add_run(".")

    if analysis['sector_stats']:
        best = analysis['sector_stats'][0]
        worst = analysis['sector_stats'][-1]
        if best['sec'] != worst['sec']:
            p = doc.add_paragraph()
            p.add_run(f"{SECTOR_LABELS[best['sec']]} led all coverage groups at ")
            pct_run(p, best['avg'])
            p.add_run(f" on average, while {SECTOR_LABELS[worst['sec']]} lagged at ")
            pct_run(p, worst['avg'])
            p.add_run(".")

    if analysis['top5']:
        top = analysis['top5'][0]
        p = doc.add_paragraph()
        p.add_run(f"{top['analyst']} posted the strongest return on the desk at ")
        pct_run(p, top['ret'])
        if analysis['bottom5'] and analysis['bottom5'][0]['analyst'] != top['analyst']:
            bot = analysis['bottom5'][0]
            p.add_run(f", while {bot['analyst']} sits at the other end at ")
            pct_run(p, bot['ret'])
        p.add_run(".")

    if analysis['rotators']:
        rot = analysis['rotators'][0]
        p = doc.add_paragraph()
        p.add_run(f"{rot['analyst']} rotated ideas the most, switching tickers on {round(rot['churn']*100)}% of reports")
        if analysis['loyalists'] and analysis['loyalists'][0]['analyst'] != rot['analyst']:
            loy = analysis['loyalists'][0]
            p.add_run(f", while {loy['analyst']} showed the most conviction, changing course on just {round(loy['churn']*100)}% of reports")
        p.add_run(".")

    if analysis['crowded']:
        t, analysts = analysis['crowded'][0]
        p = doc.add_paragraph()
        p.add_run(f"The most crowded idea in {period_label} was {t}, independently picked by {len(analysts)} different analysts ({', '.join(short_name(a) for a in analysts)}).")

    # ---- Sector scoreboard ----
    add_heading(doc, "Sector scoreboard")
    if analysis['sector_stats']:
        table = doc.add_table(rows=1, cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.LEFT
        hdr = table.rows[0].cells
        for c, text in zip(hdr, ["Sector", "Avg. return", "Analysts"]):
            c.text = text
            c.paragraphs[0].runs[0].bold = True
            shade_cell(c, "1F2430")
            c.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        for s in analysis['sector_stats']:
            row = table.add_row().cells
            row[0].text = SECTOR_LABELS[s['sec']]
            row[1].text = ''
            pr = row[1].paragraphs[0]
            pct_run(pr, s['avg'])
            row[2].text = str(s['n'])
        set_col_widths(table, [Inches(3.2), Inches(1.8), Inches(1.3)])
    else:
        doc.add_paragraph("Not enough data for this period.")

    # ---- Top / bottom performers ----
    add_heading(doc, "Top Returns")
    _add_performer_table(doc, analysis['top5'])

    add_heading(doc, "Bottom Returns")
    _add_performer_table(doc, analysis['bottom5'])

    # ---- Rotation vs conviction ----
    add_heading(doc, "Idea rotation vs. conviction")
    if analysis['rotators'] or analysis['loyalists']:
        table = doc.add_table(rows=1, cols=4)
        hdr = table.rows[0].cells
        for c, text in zip(hdr, ["Most rotation", "Changed on", "Most conviction", "Changed on"]):
            c.text = text
            c.paragraphs[0].runs[0].bold = True
            shade_cell(c, "1F2430")
            c.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        maxlen = max(len(analysis['rotators']), len(analysis['loyalists']))
        for i in range(maxlen):
            row = table.add_row().cells
            if i < len(analysis['rotators']):
                r_ = analysis['rotators'][i]
                row[0].text = r_['analyst']
                row[1].text = f"{round(r_['churn']*100)}% of reports"
            if i < len(analysis['loyalists']):
                l_ = analysis['loyalists'][i]
                row[2].text = l_['analyst']
                row[3].text = f"{round(l_['churn']*100)}% of reports"
        set_col_widths(table, [Inches(2.1), Inches(1.4), Inches(2.1), Inches(1.4)])
    else:
        doc.add_paragraph("Not enough data for this period.")

    # ---- Crowded trades ----
    add_heading(doc, "Crowded trades — picked by 2+ analysts")
    if analysis['crowded']:
        table = doc.add_table(rows=1, cols=3)
        hdr = table.rows[0].cells
        for c, text in zip(hdr, ["Ticker", "# Analysts", "Analysts"]):
            c.text = text
            c.paragraphs[0].runs[0].bold = True
            shade_cell(c, "1F2430")
            c.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        for t, analysts in analysis['crowded']:
            row = table.add_row().cells
            row[0].text = t
            row[1].text = str(len(analysts))
            row[2].text = ', '.join(short_name(a) for a in analysts)
        set_col_widths(table, [Inches(1.0), Inches(1.0), Inches(4.5)])
    else:
        doc.add_paragraph("No ticker was independently picked by 2 or more analysts in this period.")

    # ---- Methodology ----
    add_heading(doc, "Methodology & caveats", size=11, color=DIM, space_before=24)
    notes = [
        "Each analyst contributes one \u201ctop idea\u201d per monthly report. Returns are computed directly from the report's own cover price at each publication date, not from a pre-built column.",
        "When an analyst's ticker changes from one report to the next, no return is attributed to that transition \u2014 the exit price of the abandoned position isn't part of this dataset. Figures here only compound periods where a position was actually held.",
        "These are illustrative figures based on published \u201ctop idea\u201d prices, not a real, fee- or dividend-adjusted portfolio.",
    ]
    for n in notes:
        p = doc.add_paragraph(style='List Bullet')
        r = p.add_run(n)
        r.font.size = Pt(9)
        r.font.color.rgb = DIM

    doc.save(out_path)
    print(f"Wrote {out_path}")


def _add_performer_table(doc, rows):
    if not rows:
        doc.add_paragraph("Not enough data for this period.")
        return
    table = doc.add_table(rows=1, cols=3)
    hdr = table.rows[0].cells
    for c, text in zip(hdr, ["Analyst", "Coverage area", "Return"]):
        c.text = text
        c.paragraphs[0].runs[0].bold = True
        shade_cell(c, "1F2430")
        c.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    for a in rows:
        row = table.add_row().cells
        row[0].text = a['analyst']
        row[1].text = a['sector_label'] or ''
        row[2].text = ''
        pr = row[2].paragraphs[0]
        pct_run(pr, a['ret'])
    set_col_widths(table, [Inches(2.2), Inches(2.8), Inches(1.0)])


if __name__ == "__main__":
    main()
