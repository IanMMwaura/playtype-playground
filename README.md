# Playtype Playground

[Playtype Playground](https://playtype-playground.pages.dev/) is an interactive NBA analytics dashboard for exploring play-type volume and scoring efficiency. It supports player-level analysis across seasons, teams, positions, and offensive actions.

## Features

- Player landscape visualization with configurable volume and efficiency metrics
- Season, play type, team, position, and minimum-possession filters
- Player profiles with play-type statistics, percentile radar charts, and season trends
- Multi-player comparisons using shared or player-specific season spans
- Sortable efficiency leaderboards and comparison tables
- Shareable dashboard views with CSV and PNG exports

## Data

Play-type data is sourced from NBA Stats through `nba_api` and stored in a validated local cache covering the 2012-13 season onward. Player positions are assigned from the most common regular-season game listing when sufficient data is available, with the official roster position used as a fallback.

The application reads the cached dataset at startup and does not request NBA Stats data during user sessions.

## Technology

- Python
- Shiny for Python
- pandas and NumPy
- Plotly
- `nba_api`

## Local Development

Install the project dependencies and start the Shiny application from the repository root:

```powershell
python -m pip install -r playtype_playground/requirements.txt
python -m shiny run playtype_playground/app.py
```

To refresh the cached NBA dataset:

```powershell
python playtype_playground/fetch_nba_data.py
```
