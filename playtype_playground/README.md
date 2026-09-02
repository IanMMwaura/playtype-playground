# Playtype Playground

Playtype Playground is a Shiny for Python dashboard for NBA playtype data. It shows how often
players run each action and how efficiently they score from it. You can filter the
player pool, select a player from the chart, compare up to four players, and review a
player's results across seasons.

The data comes from NBA Stats through the `nba_api` package. A checked-in CSV covers
the supported seasons from 2012-13 onward. The app reads that file at startup instead
of calling NBA Stats during each session.

## Run it locally

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r playtype_playground\requirements.txt
python playtype_playground\fetch_nba_data.py
shiny run --reload playtype_playground\app.py
```

Open `http://127.0.0.1:8000` if your browser does not open automatically.

The production layout places all controls in the dashboard body. To open the retired
sidebar layout for comparison:

```powershell
$env:PLAYTYPE_PLAYGROUND_BODY_CONTROLS = "0"
shiny run --port 8765 playtype_playground\app.py
```

## What is interactive

- Season, play type, team, position, usage, and minimum-possession filters
- Swappable volume and efficiency axes
- Optional league-average crosshair, player labels, and NBA headshots
- Searchable player selection and comparison for up to four players
- Shared comparison spans or a separate career-bound span for each selected player
- Hover details for PPP, frequency, eFG%, turnover rate, and percentile
- Player overview table, multi-season percentile radar, and season history
- Sortable comparison, overview, and PPP leader tables
- Shareable filter URLs plus CSV and PNG downloads

## Refresh the NBA data

Run the fetcher whenever you want a fresh cache:

```powershell
python playtype_playground\fetch_nba_data.py
```

The command downloads PlayerIndex and SynergyPlayTypes results, reads the public NBA
game-log archive maintained by `llimllib/nba_data`, combines traded-player stints,
checks the columns and value ranges, then writes:

- `playtype_playground/data/nba_playtypes.csv`
- `playtype_playground/data/nba_playtypes.meta.json`

Choose seasons explicitly when needed:

```powershell
python playtype_playground\fetch_nba_data.py --seasons 2022-23 2023-24 2024-25
```

To update only the position assignments in an existing cache:

```powershell
python playtype_playground\fetch_nba_data.py --positions-only
```

Each player-season is assigned the guard, forward, or center spot found most often in
their regular-season game listings. At least 10 listings are required before that
majority replaces the PlayerIndex roster label. This keeps seasons with incomplete
game-log coverage on the official roster fallback.

The normalized cache uses this contract:

Required columns:

| Column | Example | Notes |
| --- | --- | --- |
| `season` | `2024-25` | Display label |
| `player_id` | `203999` | NBA player ID used for official headshots |
| `player` | `Player Name` | Player display name |
| `team` | `DEN` | Team abbreviation |
| `position` | `G`, `F`, or `C` | Most common game listing, with roster label fallback |
| `play_type` | `Isolation` | Must match a dashboard playtype label |
| `possessions` | `182` | Integer sample size |
| `frequency` | `0.184` | Fraction or percentage; values over 1 are divided by 100 |
| `ppp` | `1.087` | Points per possession |
| `efg_pct` | `54.2` | Percentage points |
| `tov_pct` | `8.7` | Percentage points |
| `score_pct` | `48.5` | Percentage points |
| `percentile` | `91` | Integer from 1 to 99 |

## Project structure

```text
playtype_playground/
├── app.py            # Shiny pages, filters, and charts
├── data_contract.py  # CSV columns and checks
├── fetch_nba_data.py # nba_api download command
├── shared.py         # Loads the cached CSV
├── data/             # CSV data and refresh metadata
├── styles.css        # Page styles and mobile layout
├── www/              # Browser assets, policies, and error page
└── requirements.txt  # Python packages
```

Only the data refresh command calls NBA Stats. The Shiny app reads the validated local
CSV.

## Before public deployment

Set the public base URL so the canonical tag, Open Graph URL, robots file, and sitemap
use the correct host:

```powershell
$env:PLAYTYPE_PLAYGROUND_CANONICAL_URL = "https://your-domain.example/"
shiny run playtype_playground\app.py
```

Update the canonical and Open Graph URLs in `www/privacy.html` and `www/terms.html` at
the same time. Review the privacy notice and terms before publishing, and add a contact
address that you monitor.
