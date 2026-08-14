# convergence-boards

Public daily output of the MLB landings board. Mirrored here so the app can
read it over `raw.githubusercontent.com`; the generator lives in a private repo.

    data/boards/{date}.txt          plain board
    data/boards/{date}-themed.txt   themed board (when a theme ran that day)
    data/themes/board-theme-{date}.json   the day's theme numbers

Generated output — edits here are overwritten by the next publish.

## Feast agent

Daily Catholic feast layer over the MLB slate — see [docs/feast-agent.md](docs/feast-agent.md).

    data/feast/{date}.html          feast board for that date
    data/feast/latest.html          most recent run
