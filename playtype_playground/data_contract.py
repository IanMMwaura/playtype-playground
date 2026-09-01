"""Checks the CSV columns used by Playtype Playground."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


app_dir = Path(__file__).parent
data_file = app_dir / "data" / "nba_playtypes.csv"
METADATA_FILE = data_file.with_suffix(".meta.json")

PLAY_TYPES = (
    "Isolation",
    "P&R Ball Handler",
    "P&R Roll Man",
    "Post Up",
    "Spot Up",
    "Transition",
    "Hand Off",
    "Cut",
    "Off Screen",
)

REQUIRED_COLUMNS = {
    "season",
    "player_id",
    "player",
    "team",
    "position",
    "play_type",
    "possessions",
    "frequency",
    "ppp",
    "efg_pct",
    "tov_pct",
    "score_pct",
    "percentile",
}

NUMERIC_COLUMNS = (
    "player_id",
    "possessions",
    "frequency",
    "ppp",
    "efg_pct",
    "tov_pct",
    "score_pct",
    "percentile",
)


def normalize_position(value: object) -> str | None:
    """Map positions such as G-F to G, F, or C."""

    text = str(value).strip().upper()
    if not text or text in {"NAN", "NONE"}:
        return None

    first = text[0]
    return first if first in {"G", "F", "C"} else None


def validate_playtype_data(frame: pd.DataFrame, *, source: str) -> pd.DataFrame:
    """Clean a dataset and reject rows the app cannot use."""

    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"{source} is missing required columns: {names}")

    result = frame.copy()
    for column in NUMERIC_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="raise")

    if not result.empty and result["frequency"].max() > 1:
        result["frequency"] = result["frequency"] / 100

    result["season"] = result["season"].astype(str)
    result["player_id"] = result["player_id"].round().astype(int)
    result["player"] = result["player"].astype(str).str.strip()
    result["team"] = result["team"].fillna("FA").astype(str).str.strip()
    result["position"] = result["position"].map(normalize_position)
    result["play_type"] = result["play_type"].astype(str).str.strip()

    invalid_positions = result["position"].isna()
    if invalid_positions.any():
        raise ValueError(f"{source} contains unsupported or missing player positions")

    unknown_play_types = sorted(set(result["play_type"]) - set(PLAY_TYPES))
    if unknown_play_types:
        names = ", ".join(unknown_play_types)
        raise ValueError(f"{source} contains unsupported play types: {names}")

    if not result["frequency"].between(0, 1).all():
        raise ValueError(f"{source} contains frequency values outside 0 through 1")
    if not result["possessions"].ge(0).all():
        raise ValueError(f"{source} contains negative possession values")
    if not result["player_id"].gt(0).all():
        raise ValueError(f"{source} contains invalid NBA player IDs")
    if not result["percentile"].between(1, 99).all():
        raise ValueError(f"{source} contains percentile values outside 1 through 99")

    key = ["season", "player", "play_type"]
    if result.duplicated(key).any():
        raise ValueError(f"{source} contains duplicate season/player/play-type rows")

    result["possessions"] = result["possessions"].round().astype(int)
    result["percentile"] = result["percentile"].round().astype(int)
    return result.sort_values(["season", "play_type", "player"], ignore_index=True)
