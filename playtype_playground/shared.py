"""Reads the cached nba_api data used by Playtype Playground."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from data_contract import (
    METADATA_FILE,
    NUMERIC_COLUMNS,
    PLAY_TYPES,
    REQUIRED_COLUMNS,
    app_dir,
    data_file,
    validate_playtype_data,
)


def _source_label(metadata_path: Path = METADATA_FILE) -> str:
    """Return the source text shown in the sidebar."""

    if not metadata_path.exists():
        return "nba_api cache"

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "nba_api cache"

    updated = str(metadata.get("fetched_at_utc", ""))[:10]
    return f"nba_api · {updated}" if updated else "nba_api cache"


def load_playtype_data(path: Path = data_file) -> tuple[pd.DataFrame, str]:
    """Read and validate a cached playtype CSV."""

    if not path.exists():
        raise FileNotFoundError(
            f"NBA dataset cache not found at {path}. "
            "Run `python playtype_playground/fetch_nba_data.py` before starting the app."
        )

    frame = pd.read_csv(path)
    frame = validate_playtype_data(frame, source=path.name)
    return frame, _source_label(path.with_suffix(".meta.json"))


playtype_data, DATA_SOURCE = load_playtype_data()


__all__ = [
    "DATA_SOURCE",
    "NUMERIC_COLUMNS",
    "PLAY_TYPES",
    "REQUIRED_COLUMNS",
    "app_dir",
    "data_file",
    "load_playtype_data",
    "playtype_data",
]
