#!/usr/bin/env python3
"""
Draws the animated SVG cards for the GitHub profile README into cards/.

    python scripts/render_readme_cards.py          real data (data/contributions.json)
    DEMO=1   -> fake data, for previewing the design only (never commit these)
    STATIC=1 -> turns animations off, shows the final frame (for screenshots)

PowerShell:  $env:DEMO="1"; $env:STATIC="1"; python scripts/render_readme_cards.py
"""
import base64
import calendar
import json
import math
import os
import random
import sys
import textwrap
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cards"
DATA = ROOT / "data" / "contributions.json"
FONTS = ROOT / "fonts"

STATIC = os.environ.get("STATIC") == "1"
DEMO = os.environ.get("DEMO") == "1"

# =====================  EDIT THIS PART  =====================
# Only put things here that are real today. Update the tiles as your projects move.
CONFIG = {
    "name": "Shabnam Kumari Soni",
    "tagline": "Software, AI and security engineer.",
    "subline": "B.Tech CSE \u00b7 RKDF University \u00b7 Bengaluru",
    "status": "Open to fresher roles",
    "accent": "#2F5BFF",   # your one brand colour
    "paper": "#FAF7F0",
    "ink": "#1B1B1B",
    "tiles": [
        {"file": "build", "label": "BUILD", "color": "#2F5BFF", "text": "#FFFFFF",
         "big": "2", "unit": "full-stack projects",
         "lines": ["AI Job Tracker", "DocQA"]},
        {"file": "ai", "label": "AI", "color": "#E8503A", "text": "#FFFFFF",
         "big": "68.8%", "unit": "DocQA eval baseline",
         "lines": ["RAG \u00b7 FastAPI \u00b7 ChromaDB"]},
        {"file": "security", "label": "SECURITY", "color": "#F2C12E", "text": "#1B1B1B",
         "big": "Next", "unit": "SecAudit",
         "lines": ["On the build list"]},
    ],
    "repos": [
        {"file": "repo1", "title": "AI Job Tracker",
         "desc": "Track job applications with a dashboard, interview dates and AI help from Gemini.",
         "tags": ["React", "Node.js", "PostgreSQL", "Docker"]},
        {"file": "repo2", "title": "DocQA",
         "desc": "Ask questions about your PDFs. Answers cite the page they came from.",
         "tags": ["FastAPI", "ChromaDB", "RAG", "React"]},
    ],
}
# ============================================================

ACCENT, PAPER, INK = CONFIG["accent"], CONFIG["paper"], CONFIG["ink"]


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    """Colour between a (t=0) and b (t=1)."""
    return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(_rgb(a), _rgb(b)))


BORDER = mix(PAPER, INK, 0.15)
MUTED = mix(INK, PAPER, 0.45)
LEVELS = [mix(PAPER, INK, 0.08)] + [mix(PAPER, ACCENT, t) for t in (0.3, 0.55, 0.8, 1.0)]

BASE_CSS = """
.serif{font-family:'HeroSerif',Georgia,'Times New Roman',serif}
.sans{font-family:'HeroSans','Segoe UI',Helvetica,Arial,sans-serif}
.rise,.pop,.swing,.pulse,.ring,.nudge{transform-box:fill-box;transform-origin:center}
.grow{transform-box:fill-box;transform-origin:bottom}
.growx{transform-box:fill-box;transform-origin:left}
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes pop{from{opacity:0;transform:scale(.2)}to{opacity:1;transform:scale(1)}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes growx{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes swing{0%{opacity:0;transform:translateY(36px) rotate(-3deg)}60%{opacity:1;transform:translateY(-6px) rotate(.5deg)}100%{opacity:1;transform:none}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.2}}
@keyframes ring{0%{opacity:.8;transform:scale(1)}100%{opacity:0;transform:scale(2.6)}}
@keyframes nudge{0%,100%{transform:translate(0,0)}50%{transform:translate(3px,-3px)}}
.rise{animation:rise .8s cubic-bezier(.2,.7,.2,1) both}
.fade{animation:fade .6s ease-out both}
.pop{animation:pop .45s cubic-bezier(.3,1.5,.5,1) both}
.grow{animation:grow .7s cubic-bezier(.2,.8,.2,1) both}
.growx{animation:growx .7s cubic-bezier(.2,.8,.2,1) both}
.swing{animation:swing 1s cubic-bezier(.2,.8,.2,1) both}
.pulse{animation:pulse 1.8s ease-in-out infinite}
.ring{animation:ring 2.4s ease-out infinite}
.nudge{animation:nudge 1.6s ease-in-out infinite}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


def _font_css():
    css = ""
    for family, fname in (("HeroSerif", "serif.woff"), ("HeroSans", "sans.woff")):
        p = FONTS / fname
        if p.exists():
            b64 = base64.b64encode(p.read_bytes()).decode()
            css += (f"@font-face{{font-family:'{family}';"
                    f"src:url(data:font/woff;base64,{b64}) format('woff')}}")
    return css


FONT_CSS = _font_css()


def dl(seconds):
    return f'style="animation-delay:{seconds:.2f}s"'


def svg(w, h, body, title):
    extra = "*{animation:none!important}" if STATIC else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{escape(title)}"><title>{escape(title)}</title>'
            f'<style>{FONT_CSS}{BASE_CSS}{extra}</style>{body}</svg>')


def card_bg(w, h):
    return (f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="20" '
            f'fill="{PAPER}" stroke="{BORDER}" stroke-width="2"/>')


# ----------------------------------------------------------------- data
def load_days():
    if DEMO:
        rnd = random.Random(7)
        end = date.today()
        return [(end - timedelta(days=364 - i), rnd.choice([0, 0, 0, 1, 2, 3, 5, 8]))
                for i in range(365)]
    if not DATA.exists():
        sys.exit("data/contributions.json not found. Run scripts/fetch_contributions.py "
                 "first, or use DEMO=1 to preview the design.")
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    return sorted((date.fromisoformat(d["date"]), int(d["count"])) for d in raw["days"])


def streaks(days):
    longest = run = 0
    for _, c in days:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    seq = [c for _, c in days]
    if seq and seq[-1] == 0:      # today may not have commits yet
        seq = seq[:-1]
    current = 0
    for c in reversed(seq):
        if c > 0:
            current += 1
        else:
            break
    return current, longest


# ----------------------------------------------------------------- cards
def portrait_svg():
    """Dot portrait from data/portrait.json (made by scripts/make_portrait.py), or None."""
    f = ROOT / "data" / "portrait.json"
    if not f.exists():
        return None
    p = json.loads(f.read_text(encoding="utf-8"))
    pitch = p["pitch"]
    width, height = p["cols"] * pitch, p["rows"] * pitch
    x0, y0 = 1000 - 40 - width, (300 - height) / 2
    rows = defaultdict(list)
    for row, col, r in p["dots"]:
        rows[row].append(f'<circle cx="{x0 + (col + .5) * pitch:.1f}" cy="{y0 + (row + .5) * pitch:.1f}" r="{r}"/>')
    # one group per row, fading in top to bottom like a slow printer
    return "".join(f'<g class="fade" {dl(.8 + row * 0.03)} fill="{INK}">{"".join(c)}</g>'
                   for row, c in sorted(rows.items()))


def hero():
    c = CONFIG
    pic = portrait_svg()
    if pic:
        left = f"""
<text class="sans rise" {dl(.1)} x="56" y="68" font-size="15" letter-spacing="4" fill="{MUTED}">HELLO</text>
<text class="serif rise" {dl(.3)} x="54" y="138" font-size="60" fill="{INK}">{escape(c['name'])}</text>
<rect class="growx" {dl(.9)} x="56" y="158" width="140" height="6" rx="3" fill="{ACCENT}"/>
<text class="sans rise" {dl(1.0)} x="56" y="204" font-size="24" fill="{INK}">{escape(c['tagline'])}</text>
<text class="sans rise" {dl(1.2)} x="56" y="232" font-size="16" fill="{MUTED}">{escape(c['subline'])}</text>
<g class="rise" {dl(1.4)}>
  <rect x="56" y="runY" width="240" height="40" rx="20" fill="none" stroke="{BORDER}" stroke-width="2"/>
  <circle class="ring" cx="80" cy="runC" r="5" fill="none" stroke="{ACCENT}" stroke-width="2"/>
  <circle class="pulse" cx="80" cy="runC" r="5" fill="{ACCENT}"/>
  <text class="sans" x="96" y="runT" font-size="15" fill="{INK}">{escape(c['status'])}</text>
</g>
{pic}
""".replace("runY", "248").replace("runC", "268").replace("runT", "273")
    else:
        dots = []
        for col in range(8):
            for row in range(4):
                strength = 0.12 + 0.8 * abs(math.sin(col * 1.3 + row * 0.9))
                dots.append(f'<circle class="pop" {dl(1.0 + (col + row) * 0.06)} '
                            f'cx="{740 + col * 22}" cy="{204 + row * 22}" r="5" '
                            f'fill="{mix(PAPER, ACCENT, strength)}"/>')
        left = f"""
<text class="sans rise" {dl(.1)} x="56" y="78" font-size="15" letter-spacing="4" fill="{MUTED}">HELLO</text>
<text class="serif rise" {dl(.3)} x="54" y="160" font-size="76" fill="{INK}">{escape(c['name'])}</text>
<rect class="growx" {dl(.9)} x="56" y="182" width="140" height="6" rx="3" fill="{ACCENT}"/>
<text class="sans rise" {dl(1.0)} x="56" y="234" font-size="26" fill="{INK}">{escape(c['tagline'])}</text>
<text class="sans rise" {dl(1.2)} x="56" y="266" font-size="16" fill="{MUTED}">{escape(c['subline'])}</text>
<g class="rise" {dl(1.4)}>
  <rect x="704" y="48" width="240" height="40" rx="20" fill="none" stroke="{BORDER}" stroke-width="2"/>
  <circle class="ring" cx="728" cy="68" r="5" fill="none" stroke="{ACCENT}" stroke-width="2"/>
  <circle class="pulse" cx="728" cy="68" r="5" fill="{ACCENT}"/>
  <text class="sans" x="744" y="73" font-size="15" fill="{INK}">{escape(c['status'])}</text>
</g>
{''.join(dots)}
"""
    return svg(1000, 300, card_bg(1000, 300) + left, f"{c['name']} - {c['tagline']}")


def heatmap(days):
    cell, pitch = 14, 17
    offset = (days[0][0].weekday() + 1) % 7          # Sunday = row 0
    ncols = (len(days) + offset + 6) // 7
    x0 = (1000 - (ncols * pitch - 3)) / 2
    y0 = 86
    mx = max(c for _, c in days) or 1
    total = sum(c for _, c in days)
    rects, labels = [], []
    for i, (d, c) in enumerate(days):
        col, row = divmod(i + offset, 7)
        lvl = 0 if c == 0 else max(1, min(4, math.ceil(4 * c / mx)))
        rects.append(f'<rect class="pop" {dl(1.6 + col * 0.02)} x="{x0 + col * pitch:.1f}" '
                     f'y="{y0 + row * pitch}" width="{cell}" height="{cell}" rx="3" fill="{LEVELS[lvl]}"/>')
        if d.day == 1:
            labels.append(f'<text class="sans" x="{x0 + col * pitch:.1f}" y="74" font-size="12" '
                          f'fill="{MUTED}">{calendar.month_abbr[d.month]}</text>')
    legend = [f'<text class="sans" x="770" y="236" font-size="12" text-anchor="end" fill="{MUTED}">Less</text>']
    legend += [f'<rect x="{778 + i * 16}" y="226" width="12" height="12" rx="3" fill="{LEVELS[i]}"/>'
               for i in range(5)]
    legend.append(f'<text class="sans" x="864" y="236" font-size="12" fill="{MUTED}">More</text>')
    body = f"""
{card_bg(1000, 252)}
<text class="serif rise" {dl(1.3)} x="48" y="46" font-size="26" fill="{INK}">Contributions, last year</text>
<text class="sans rise" {dl(1.3)} x="952" y="44" font-size="16" text-anchor="end" fill="{MUTED}">{total:,} in total</text>
{''.join(labels)}{''.join(rects)}{''.join(legend)}
"""
    return svg(1000, 252, body, f"Contribution graph: {total} contributions in the last year")


def activity(days):
    last = days[-1][0]
    months, y, m = [], last.year, last.month
    for _ in range(12):
        months.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months.reverse()
    sums = defaultdict(int)
    for d, c in days:
        sums[(d.year, d.month)] += c
    vals = [sums[k] for k in months]
    mx = max(vals) or 1
    best = vals.index(max(vals))

    base_y, max_h, x0, pitch, bw = 250, 140, 56, 50, 34
    bars = []
    for i, ((yy, mm), v) in enumerate(zip(months, vals)):
        h = max(3, v / mx * max_h)
        x = x0 + i * pitch
        fill = ACCENT if i == best else mix(PAPER, INK, 0.16)
        bars.append(f'<rect class="grow" {dl(2.0 + i * 0.06)} x="{x}" y="{base_y - h:.1f}" width="{bw}" '
                    f'height="{h:.1f}" rx="6" fill="{fill}"/>')
        bars.append(f'<text class="sans" x="{x + bw / 2}" y="274" font-size="12" text-anchor="middle" '
                    f'fill="{MUTED}">{calendar.month_abbr[mm]}</text>')
        if i == best and v > 0:
            bars.append(f'<text class="sans pop" {dl(3.0)} x="{x + bw / 2}" y="{base_y - h - 10:.1f}" '
                        f'font-size="14" font-weight="700" text-anchor="middle" fill="{ACCENT}">{v}</text>')

    cur, longest = streaks(days)
    top_day, top_count = max(days, key=lambda t: t[1])
    stats = [
        (f"{sum(c for _, c in days):,}", "Contributions"),
        (str(cur), "Current streak (days)"),
        (str(longest), "Longest streak (days)"),
        (str(top_count), f"Busiest day \u00b7 {calendar.month_abbr[top_day.month]} {top_day.day}"),
    ]
    cells = []
    for i, (num, label) in enumerate(stats):
        x, y = 690 + (i % 2) * 140, 120 + (i // 2) * 105
        cells.append(f'<g class="rise" {dl(2.4 + i * 0.15)}>'
                     f'<text class="serif" x="{x}" y="{y}" font-size="44" fill="{INK}">{escape(num)}</text>'
                     f'<text class="sans" x="{x}" y="{y + 24}" font-size="13" fill="{MUTED}">{escape(label)}</text></g>')
    body = f"""
{card_bg(1000, 300)}
<text class="serif rise" {dl(1.9)} x="56" y="56" font-size="26" fill="{INK}">Contributions per month</text>
<line x1="48" y1="{base_y}" x2="650" y2="{base_y}" stroke="{BORDER}" stroke-width="2"/>
{''.join(bars)}{''.join(cells)}
"""
    return svg(1000, 300, body, "Monthly contributions with streak stats")


def tile(i, t):
    tc = t["text"]
    lines = "".join(
        f'<text class="sans" x="26" y="{178 + k * 20}" font-size="14" fill="{tc}" opacity=".85">{escape(s)}</text>'
        for k, s in enumerate(t["lines"]))
    body = f"""
<g transform="translate(0,8)"><g class="swing" {dl(3.0 + i * 0.25)}>
  <rect x="0" y="0" width="330" height="220" rx="20" fill="{t['color']}"/>
  <text class="sans" x="26" y="42" font-size="14" font-weight="700" letter-spacing="3" fill="{tc}">{escape(t['label'])}</text>
  <circle class="ring" cx="296" cy="36" r="6" fill="none" stroke="{tc}" stroke-width="2"/>
  <circle cx="296" cy="36" r="4" fill="{tc}"/>
  <text class="serif pop" {dl(3.4 + i * 0.25)} x="24" y="122" font-size="64" fill="{tc}">{escape(t['big'])}</text>
  <text class="sans" x="26" y="148" font-size="15" fill="{tc}">{escape(t['unit'])}</text>
  {lines}
  <g transform="translate(284,172)"><path class="nudge" d="M0 14 L14 0 M3 0 H14 V11" fill="none"
     stroke="{tc}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></g>
</g></g>
"""
    return svg(330, 236, body, f"{t['label']}: {t['big']} {t['unit']}")


def repo(i, r):
    lines = textwrap.wrap(r["desc"], 54)[:3]
    text = "".join(f'<text class="sans" x="26" y="{80 + k * 20}" font-size="14" fill="{MUTED}">{escape(s)}</text>'
                  for k, s in enumerate(lines))
    pills, x = [], 26
    for tag in r["tags"]:
        w = len(tag) * 7.4 + 22
        pills.append(f'<rect x="{x:.1f}" y="136" width="{w:.1f}" height="26" rx="13" fill="{mix(PAPER, ACCENT, .12)}"/>'
                     f'<text class="sans" x="{x + w / 2:.1f}" y="153" font-size="12" text-anchor="middle" '
                     f'fill="{ACCENT}">{escape(tag)}</text>')
        x += w + 8
    body = f"""
{card_bg(490, 184)}
<g class="rise" {dl(3.9 + i * 0.2)}>
  <text class="serif" x="26" y="50" font-size="28" fill="{INK}">{escape(r['title'])}</text>
  <g transform="translate(446,30)"><path class="nudge" d="M0 14 L14 0 M3 0 H14 V11" fill="none"
     stroke="{ACCENT}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></g>
  {text}{''.join(pills)}
</g>
"""
    return svg(490, 184, body, f"Project: {r['title']}")


# ----------------------------------------------------------------- main
def main():
    OUT.mkdir(exist_ok=True)
    days = load_days()
    files = {"hero": hero(), "heatmap": heatmap(days), "activity": activity(days)}
    for i, t in enumerate(CONFIG["tiles"]):
        files[t["file"]] = tile(i, t)
    for i, r in enumerate(CONFIG["repos"]):
        files[r["file"]] = repo(i, r)
    for name, content in files.items():
        (OUT / f"{name}.svg").write_text(content, encoding="utf-8")
    mode = ("DEMO data, " if DEMO else "") + ("static" if STATIC else "animated")
    print(f"Wrote {len(files)} cards to {OUT} ({mode})")


if __name__ == "__main__":
    main()
