"""Render the public GitHub contribution calendar as light/dark SVGs.

Reads https://github.com/users/<user>/contributions (the same data visitors
see, private contributions included when the profile setting is on).
Usage: python scripts/contributions.py <user> <out_dir>
"""
import datetime as dt
import html
import re
import sys
import urllib.request

USER, OUT = sys.argv[1], sys.argv[2]
req = urllib.request.Request(f"https://github.com/users/{USER}/contributions",
                             headers={"User-Agent": "Mozilla/5.0 profile-readme"})
page = urllib.request.urlopen(req, timeout=30).read().decode()

cells = {}  # id -> (date, level)
for td in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", page):
    d = re.search(r'data-date="([\d-]+)"', td)
    i = re.search(r'id="([^"]+)"', td)
    lv = re.search(r'data-level="(\d)"', td)
    if d and i and lv:
        cells[i.group(1)] = (dt.date.fromisoformat(d.group(1)), int(lv.group(1)))
counts = {}
for for_id, text in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', page):
    m = re.match(r"([\d,]+) contribution", text)
    counts[for_id] = int(m.group(1).replace(",", "")) if m else 0
days = sorted((date, lv, counts.get(i, 0)) for i, (date, lv) in cells.items())
if len(days) < 300:
    sys.exit(f"parsed only {len(days)} days, page layout changed?")

total = sum(c for *_, c in days)
last = days[-1][0]
recent = sum(c for d, _, c in days if d > last - dt.timedelta(days=30))

THEMES = {
    "light": dict(panel="#ffffff", stroke="#d1d9e0", fg="#1f2328", muted="#59636e", accent="#1a7f37",
                  lv=["#eff2f5", "#aceebb", "#4ac26b", "#2da44e", "#116329"]),
    "dark": dict(panel="#0d1117", stroke="#3d444d", fg="#f0f6fc", muted="#9198a1", accent="#3fb950",
                 lv=["#151b23", "#033a16", "#196c2e", "#2ea043", "#56d364"]),
}
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
C, G = 11, 2
PITCH = C + G
P, LEFT, TOP = 20, 30, 66
start = days[0][0] - dt.timedelta(days=(days[0][0].weekday() + 1) % 7)  # Sunday-start weeks
weeks = (last - start).days // 7 + 1
W = P + LEFT + weeks * PITCH - G + P
H = TOP + 7 * PITCH - G + 40


def render(t):
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
         f'aria-label="{total:,} contributions in the last year">',
         f'<title>{total:,} contributions in the last year, {recent} in the last 30 days</title>',
         f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="8" fill="{t["panel"]}" stroke="{t["stroke"]}"/>',
         f'<g font-family="{FONT}">',
         f'<text x="{P}" y="32" fill="{t["fg"]}" font-size="15" font-weight="600">{total:,} contributions in the last year</text>',
         f'<text x="{W-P}" y="32" fill="{t["accent"]}" font-size="15" font-weight="600" text-anchor="end">{recent} in the last 30 days</text>']
    gx = P + LEFT
    for r, lab in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        o.append(f'<text x="{P}" y="{TOP + r*PITCH + 9}" fill="{t["muted"]}" font-size="10">{lab}</text>')
    prev_m, last_w = start.month, -9
    for w in range(weeks):
        d = start + dt.timedelta(weeks=w)
        if d.month != prev_m:
            if w - last_w >= 3 and w <= weeks - 3:
                o.append(f'<text x="{gx + w*PITCH}" y="{TOP-8}" fill="{t["muted"]}" font-size="10">{d:%b}</text>')
                last_w = w
            prev_m = d.month
    for date, lv, c in days:
        w = (date - start).days // 7
        r = (date.weekday() + 1) % 7
        o.append(f'<rect x="{gx + w*PITCH}" y="{TOP + r*PITCH}" width="{C}" height="{C}" rx="2" fill="{t["lv"][lv]}">'
                 f'<title>{c} on {date:%b %-d}</title></rect>')
    ly = H - 18
    o.append(f'<text x="{P}" y="{ly+9}" fill="{t["muted"]}" font-size="10">Updated {last:%-d %b %Y} · all repositories, private included</text>')
    lx = W - P - 5 * PITCH - 28
    o.append(f'<text x="{lx - 6}" y="{ly+9}" fill="{t["muted"]}" font-size="10" text-anchor="end">Less</text>')
    for k in range(5):
        o.append(f'<rect x="{lx + k*PITCH}" y="{ly}" width="{C}" height="{C}" rx="2" fill="{t["lv"][k]}"/>')
    o.append(f'<text x="{lx + 5*PITCH + 4}" y="{ly+9}" fill="{t["muted"]}" font-size="10">More</text>')
    o.append("</g></svg>")
    return "\n".join(o) + "\n"


for name, t in THEMES.items():
    with open(f"{OUT}/contributions-{name}.svg", "w") as f:
        f.write(render(t))
print(f"{len(days)} days, {total} total, {recent} last 30d")
