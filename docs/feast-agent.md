# Feast Agent

Daily Catholic feast layer board, zero AI cost. Full-roster coverage,
no factorization, JESUIT ORDER lock asserted at startup.

## Install (one time, ~2 minutes)

1. In your `convergence-boards` repo, add:
   - `feast_agent.py` → repo root
   - `feasts.json` → repo root (merge with your existing one — same founders.json
     spirit; schema documented inside; 14 dates pre-baked through 8/29)
   - `feast-agent.yml` → `.github/workflows/feast-agent.yml`
2. Commit + push. Done — runs daily at 9:00 AM ET.
3. Manual rerun anytime: repo → Actions → feast-agent → Run workflow.

## Viewing on your phone

Enable GitHub Pages (repo Settings → Pages → deploy from `main`), then bookmark:

    https://taxwrities.github.io/convergence-boards/data/feast/latest.html

Renders styled. (raw.githubusercontent serves HTML as plain text — Pages is the fix.)

## What it does daily

- Loads the feast for the date (or falls back to date-numerology-only)
- Builds the pool: phrase ciphers ×7, death year, anniversary span (as-is),
  death age, date numerology, day-of-year, days-left
- Pulls the full MLB slate + probables + active rosters (MLB Stats API)
- Scans EVERY player, full name + surname — zero-hit players still listed
- Marks names that appear in that day's convergence board txt (▸board)
- Shades standouts: 3+ hits, or any hit on a multi-source pool number
- Writes `data/feast/YYYY-MM-DD.html` + `latest.html`

## Extending

Add saints to `feasts.json` entries — blurbs and narratives are pre-baked
there so routing costs nothing daily. Tests: `python3 feast_agent.py 2026-08-13`
locally to regenerate any date.
