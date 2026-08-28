#!/usr/bin/env python3
"""
FEAST AGENT — daily Catholic feast layer scanner
Runs free of AI: loads feasts.json, builds the day pool, pulls the MLB slate
and active rosters from the MLB Stats API, scans EVERY player (full name +
surname) through the ciphers, overlays the convergence board if present, and
emits a styled HTML board.

Rules honored:
  - No factorization: numbers count as-is or not at all.
  - Full coverage: every rostered player on every game, hits or not.
  - Regression lock asserted at startup (JESUIT ORDER 144/54/153/72/529).

Usage:
  python3 feast_agent.py                # today (US/Eastern)
  python3 feast_agent.py 2026-08-13     # specific date
Outputs:
  data/feast/YYYY-MM-DD.html  and  data/feast/latest.html
"""

import json, sys, os, re, unicodedata, urllib.request
from datetime import datetime, date, timezone, timedelta

# ---------------------------------------------------------------- ciphers ---
JEW = {**{chr(65+i): v for i, v in enumerate([1,2,3,4,5,6,7,8,9])},
       'J':600,'K':10,'L':20,'M':30,'N':40,'O':50,'P':60,'Q':70,'R':80,
       'S':90,'T':100,'U':200,'V':700,'W':900,'X':300,'Y':400,'Z':500}
CHALD = {'A':1,'B':2,'C':3,'D':4,'E':5,'F':8,'G':3,'H':5,'I':1,'J':1,'K':2,
         'L':3,'M':4,'N':5,'O':7,'P':8,'Q':1,'R':2,'S':3,'T':4,'U':6,'V':6,
         'W':6,'X':5,'Y':1,'Z':7}

def _letters(s):
    s = unicodedata.normalize('NFD', s.upper())
    return [c for c in s if 'A' <= c <= 'Z']

def ordinal(s):        return sum(ord(c)-64 for c in _letters(s))
def reduction(s):      return sum(((ord(c)-65) % 9)+1 for c in _letters(s))
def rev_ordinal(s):    return sum(27-(ord(c)-64) for c in _letters(s))
def rev_reduction(s):  return sum(((26-(ord(c)-64)) % 9)+1 for c in _letters(s))
def satanic(s):        return sum(ord(c)-64+35 for c in _letters(s))
def jewish(s):         return sum(JEW[c] for c in _letters(s))
def chaldean(s):       return sum(CHALD[c] for c in _letters(s))

CIPHERS = [("Ord", ordinal), ("Red", reduction), ("RevO", rev_ordinal),
           ("RevR", rev_reduction), ("Sat", satanic), ("Jew", jewish),
           ("Chald", chaldean)]

def all_values(s):
    return {name: fn(s) for name, fn in CIPHERS}

# regression lock — abort loudly if cipher math ever drifts
_lock = all_values("JESUIT ORDER")
assert (_lock["Ord"], _lock["Red"], _lock["RevO"], _lock["RevR"], _lock["Sat"]) \
       == (144, 54, 153, 72, 529), f"REGRESSION LOCK FAILED: {_lock}"

# ------------------------------------------------------------- date math ---
def date_numerology(d: date):
    m, dd, yy = d.month, d.day, d.year
    c, y2 = divmod(yy, 100)
    return {
        f"{m}+{dd}+{c}+{y2}": m+dd+c+y2,
        f"{m}+{dd}+digits":   m+dd+sum(int(x) for x in str(yy)),
        f"{m}+{dd}+{y2}":     m+dd+y2,
        f"{m}+{dd}":          m+dd,
    }

# ------------------------------------------------------------- day pool ----
def build_pool(entry, d: date):
    """pool: value -> list of labels. Numbers enter AS-IS only."""
    pool = {}
    def add(v, label):
        if v is None or v <= 0: return
        pool.setdefault(v, []).append(label)

    for phrase in entry["phrases"]:
        for cname, v in all_values(phrase).items():
            add(v, f"{phrase} {cname}")

    if entry.get("death_year"):
        add(entry["death_year"], "death year")
        add(d.year - entry["death_year"], "death anniversary span")
    if entry.get("age"):
        add(entry["age"], "death age")

    for label, v in date_numerology(d).items():
        add(v, f"date num {label}")
    doy = d.timetuple().tm_yday
    add(doy, "day of year")
    add((date(d.year, 12, 31).timetuple().tm_yday) - doy, "days left")
    return pool

# ------------------------------------------------------------ mlb pulls ----
API = "https://statsapi.mlb.com/api/v1"

def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "feast-agent/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def slate(d: date):
    data = _get(f"{API}/schedule?sportId=1&date={d.isoformat()}"
                "&hydrate=probablePitcher,team")
    games = []
    for day in data.get("dates", []):
        for g in day.get("games", []):
            games.append({
                "away": g["teams"]["away"]["team"],
                "home": g["teams"]["home"]["team"],
                "time": g.get("gameDate", ""),
                "away_sp": g["teams"]["away"].get("probablePitcher", {}).get("fullName"),
                "home_sp": g["teams"]["home"].get("probablePitcher", {}).get("fullName"),
            })
    return games

def roster(team_id):
    try:
        data = _get(f"{API}/teams/{team_id}/roster?rosterType=active")
        return [p["person"]["fullName"] for p in data.get("roster", [])]
    except Exception:
        return []

def callups(d: date):
    """Players recalled/selected TODAY — elevation carriers ('taken up')."""
    try:
        data = _get(f"{API}/transactions?startDate={d.isoformat()}"
                    f"&endDate={d.isoformat()}")
        up = set()
        for t in data.get("transactions", []):
            desc = (t.get("description") or "").lower()
            if any(k in desc for k in ("recalled", "selected the contract",
                                       "contract purchased", "called up")):
                p = t.get("person", {}).get("fullName")
                if p: up.add(p)
        return up
    except Exception:
        return set()

# ------------------------------------------------------- board overlay -----
BOARD_URL = ("https://raw.githubusercontent.com/taxwrities/convergence-boards/"
             "main/data/boards/{}.txt")

def board_text(d: date):
    try:
        return _get_text(BOARD_URL.format(d.isoformat()))
    except Exception:
        return ""

def _get_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "feast-agent/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()

# ----------------------------------------------------------------- scan ----
def scan_name(name, pool):
    """full-name hits + surname-only hits (deduped), no factorization."""
    hits = []
    for cname, v in all_values(name).items():
        for label in pool.get(v, []):
            hits.append(("full", cname, v, label))
    parts = name.split()
    if len(parts) > 1:
        seen = {(h[1], h[2]) for h in hits}
        for cname, v in all_values(parts[-1]).items():
            if (cname, v) in seen:
                continue
            for label in pool.get(v, []):
                hits.append(("last", cname, v, label))
    return hits

def root_flags(name, lexicon, wanted):
    """Etymology/translation puns, checked mechanically: any lexicon root
    inside the name whose meaning is on today's wanted list gets flagged.
    (Montgomery rule: MONT = mount on Dormition day should never be missed
    by a human again.)"""
    n = " " + "".join(c for c in __import__("unicodedata").normalize(
        "NFD", name.upper()) if c.isalpha() or c == " ") + " "
    out = []
    for root, meaning in lexicon.items():
        if meaning in wanted and root in n:
            out.append(f"⚑ {root.strip()}→{meaning.split('-')[0].upper()}")
    return out

# ----------------------------------------------------------------- html ----
CSS = """
:root{--ink:#1a1410;--parchment:#f0e7d8;--card:#faf5ea;--martyr:#8e1c1c;
--martyrb:#b3261e;--gold:#9a7b2d;--muted:#6f6353;--rule:#d3c5aa}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--parchment);color:var(--ink);font-family:Georgia,serif;
font-size:14px;line-height:1.4;padding:16px 10px 40px;max-width:620px;margin:0 auto}
.eyebrow{font-family:'Courier New',monospace;font-size:11px;letter-spacing:.14em;
text-transform:uppercase;color:var(--martyr);font-weight:bold}
h1{font-size:25px;font-style:italic;font-weight:normal;margin:4px 0 2px}
.sub{color:var(--muted);font-size:12.5px;margin-bottom:6px}
.blurb{background:var(--card);border:1px solid var(--rule);border-left:4px solid
var(--martyr);border-radius:4px;padding:10px 12px;font-size:13.5px;margin:10px 0 14px}
.poolbox{background:var(--card);border:1px solid var(--rule);border-radius:4px;
padding:8px 10px;margin-bottom:16px;font-family:'Courier New',monospace;font-size:11px;
line-height:1.7;color:#3a3226}
.poolbox b{color:var(--martyrb)}
.game{margin-bottom:20px}
.gamehead{background:var(--ink);color:var(--card);border-radius:6px 6px 0 0;padding:9px 12px}
.gamehead h2{font-size:16px;font-weight:normal;font-style:italic}
.gamehead .frame{font-size:11.5px;color:#cfc4ad;margin-top:2px;font-family:'Courier New',monospace}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid
var(--rule);border-top:none;border-radius:0 0 6px 6px;overflow:hidden}
td{padding:6px 8px;border-top:1px solid var(--rule);vertical-align:top;font-size:12.5px}
td:first-child{font-weight:bold;width:33%;font-size:13px}
tr.big{background:#f6ece0;border-left:4px solid var(--martyrb)}
tr.none td:last-child{color:var(--muted);font-style:italic}
tr.onboard td:first-child::after{content:" ▸board";font-family:'Courier New',monospace;
font-size:9px;color:var(--gold);font-weight:normal}
.n{font-family:'Courier New',monospace;font-weight:bold;color:var(--martyrb)}
.pit{font-family:'Courier New',monospace;font-size:10px;letter-spacing:.08em;
text-transform:uppercase;color:var(--gold)}
.foot{margin-top:14px;font-size:12px;color:var(--muted);font-style:italic;
border-top:1px solid var(--rule);padding-top:10px}
"""

def fmt_hits(hits):
    if not hits:
        return "—"
    parts = []
    for scope, cname, v, label in hits:
        pre = "" if scope == "full" else "last "
        parts.append(f'{pre}{cname} <span class="n">{v}</span>={label}')
    return "; ".join(parts)

def render(d, entry, games_out, pool, board_present):
    doy = d.timetuple().tm_yday
    left = date(d.year, 12, 31).timetuple().tm_yday - doy
    nums = " / ".join(str(v) for v in date_numerology(d).values())
    top = sorted(((v, ls) for v, ls in pool.items() if len(ls) > 1),
                 key=lambda x: -len(x[1]))[:8]
    poolrows = "<br>".join(
        f"<b>{v}</b> ← " + " · ".join(ls) for v, ls in top) or "single-source pool"

    html = [f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Feast Agent — {d.isoformat()}</title><style>{CSS}</style></head><body>
<div class="eyebrow">Feast agent · auto-generated · {d.strftime('%a')} {d.month}/{d.day}/{d.year}</div>
<h1>{entry['name']}</h1>
<div class="sub">Day {doy} / {left} left · date num {nums} · liturgical layer over the full MLB slate</div>
<div class="blurb">{entry['blurb']}<br><i>Narratives: {'; '.join(entry['narratives'])}</i></div>
<div class="poolbox"><b>Converged pool numbers</b> (multi-source)<br>{poolrows}</div>"""]

    for g in games_out:
        html.append(f"""<div class="game"><div class="gamehead">
<h2>{g['title']}</h2><div class="frame">{g['frame']}</div></div><table>""")
        for row in g["rows"]:
            cls = []
            if row["big"]: cls.append("big")
            if not row["hits"]: cls.append("none")
            if row["onboard"]: cls.append("onboard")
            name_cell = (f'<span class="pit">SP </span>{row["name"]}'
                         if row["sp"] else row["name"])
            cell = fmt_hits(row["hits"])
            if row.get("flags"):
                cell = "<b>" + " · ".join(row["flags"]) + "</b>" + \
                       ("; " + cell if cell != "—" else "")
            html.append(f'<tr class="{" ".join(cls)}"><td>{name_cell}</td>'
                        f'<td>{cell}</td></tr>')
        html.append("</table></div>")

    board_note = ("▸board marks names appearing in today's convergence board file."
                  if board_present else
                  "No convergence board file found for today — feast layer only.")
    total = sum(len(g["rows"]) for g in games_out)
    html.append(f'<div class="foot">{total} names scanned, all shown. '
                f'Numbers as-is only — no factorization. ▲ = called up today '
                f'(elevation carrier). {board_note}</div>'
                "</body></html>")
    return "".join(html)

# ----------------------------------------------------------------- main ----
def published_date(out_dir):
    """Date of the currently published latest.html, or None if absent/unreadable.
    Read back from the <title> the renderer writes, so there is no sidecar file
    to drift out of sync with the page itself."""
    try:
        with open(os.path.join(out_dir, "latest.html"), encoding="utf-8") as f:
            m = re.search(r"<title>Feast Agent . (\d{4}-\d{2}-\d{2})</title>",
                          f.read(8192))
        return date.fromisoformat(m.group(1)) if m else None
    except (OSError, ValueError):
        return None


def main():
    now = datetime.now(timezone.utc)
    if len(sys.argv) > 1:
        d = date.fromisoformat(sys.argv[1])
        explicit = True
    else:  # US/Eastern "today" regardless of runner timezone
        d = (now - timedelta(hours=4)).date()
        explicit = False

    # Resolved date is logged before any work, so a run that fired hours late is
    # visible in the Actions log rather than being inferred from the output.
    print(f"feast agent: resolved date {d.isoformat()} "
          f"({'CLI argument' if explicit else 'derived from ET clock'}); "
          f"UTC now {now:%Y-%m-%d %H:%M}")

    feasts = json.load(open(os.path.join(os.path.dirname(__file__) or ".",
                                         "feasts.json"), encoding="utf-8"))
    key = d.strftime("%m-%d")
    entry = next((e for e in feasts["entries"] if e["feast"] == key), None)
    if entry is None:
        entry = {"name": f"(no feast entry for {key})", "phrases": [],
                 "narratives": ["add this date to feasts.json"],
                 "blurb": "No saint filed for this date yet — date numerology only.",
                 "death_year": None, "age": None}

    pool = build_pool(entry, d)
    board = board_text(d)
    games = slate(d)
    up_today = callups(d)
    lexicon = feasts.get("_roots", {})
    wanted = set(entry.get("roots", []))

    # threshold for shading: 3+ hits or any hit on a multi-source pool number
    def is_big(hits):
        return len(hits) >= 3 or any(len(pool.get(h[2], [])) > 1 for h in hits)

    games_out = []
    for g in games:
        rows = []
        names = []
        for side in ("away", "home"):
            for n in roster(g[side]["id"]):
                names.append((n, False))
        for sp in (g["away_sp"], g["home_sp"]):
            if sp:
                names.append((sp, True))
        seen = set()
        for n, sp in names:
            if n in seen: continue
            seen.add(n)
            hits = scan_name(n, pool)
            up = n in up_today
            flags = root_flags(n, lexicon, wanted)
            rows.append({"name": ("▲ " + n) if up else n, "sp": sp,
                         "hits": hits, "flags": flags,
                         "big": is_big(hits) or up or bool(flags),
                         "onboard": bool(board) and n in board})
        rows.sort(key=lambda r: (not r["sp"], -len(r["hits"])))
        t = g["time"][11:16] if len(g["time"]) >= 16 else ""
        games_out.append({
            "title": f"{g['away']['abbreviation']} @ {g['home']['abbreviation']}"
                     + (f" · {t}Z" if t else ""),
            "frame": " · ".join(filter(None, [
                f"{g['away_sp'] or 'TBD'} v {g['home_sp'] or 'TBD'}"])),
            "rows": rows})

    out_dir = os.path.join(os.path.dirname(__file__) or ".", "data", "feast")
    os.makedirs(out_dir, exist_ok=True)
    page = render(d, entry, games_out, pool, bool(board))

    # The dated file is always written — regenerating any past day is supported
    # and harmless, since it only ever touches that day's own file.
    targets = [f"{d.isoformat()}.html"]

    # latest.html is the bookmark, so it must never move backwards. A run that
    # slipped past the ET midnight boundary, or a manual regen of an older date
    # (the README documents `feast_agent.py 2026-08-13`), would otherwise
    # silently republish a stale board under the live URL.
    prev = published_date(out_dir)
    if prev is not None and prev > d:
        print(f"feast agent: REFUSING to regress latest.html — published board "
              f"is {prev.isoformat()}, this run resolved {d.isoformat()}. "
              f"Wrote {d.isoformat()}.html only; latest.html left untouched.")
    else:
        targets.append("latest.html")

    for fname in targets:
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8",
                  newline="\n") as f:
            f.write(page)
    print(f"feast agent wrote {len(games_out)} games -> {out_dir} "
          f"({', '.join(targets)})")

if __name__ == "__main__":
    main()
