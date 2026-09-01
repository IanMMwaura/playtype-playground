"""Downloads NBA Synergy playtype data and stores the app's local CSV."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import time
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

import pandas as pd
from nba_api.stats.endpoints import playerindex, synergyplaytypes

from data_contract import (
    PLAY_TYPES,
    data_file,
    normalize_position,
    validate_playtype_data,
)


DEFAULT_SEASONS = tuple(f"{year}-{str(year + 1)[-2:]}" for year in range(2012, 2026))
PLAY_TYPE_PARAMETERS = {
    "Isolation": "Isolation",
    "P&R Ball Handler": "PRBallHandler",
    "P&R Roll Man": "PRRollman",
    "Post Up": "Postup",
    "Spot Up": "Spotup",
    "Transition": "Transition",
    "Hand Off": "Handoff",
    "Cut": "Cut",
    "Off Screen": "OffScreen",
}

SYNERGY_COLUMNS = {
    "PLAYER_ID",
    "PLAYER_NAME",
    "TEAM_ABBREVIATION",
    "PERCENTILE",
    "POSS_PCT",
    "PPP",
    "TOV_POSS_PCT",
    "SCORE_POSS_PCT",
    "EFG_PCT",
    "POSS",
    "PTS",
    "FGA",
}
PLAYER_INDEX_COLUMNS = {"PERSON_ID", "POSITION"}

T = TypeVar("T")


def _require_columns(frame: pd.DataFrame, expected: set[str], label: str) -> None:
    missing = expected.difference(frame.columns)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"{label} response is missing columns: {names}")


def _weighted_average(group: pd.DataFrame, column: str, weight: str) -> float:
    values = pd.to_numeric(group[column], errors="coerce")
    weights = pd.to_numeric(group[weight], errors="coerce").fillna(0).clip(lower=0)
    valid = values.notna() & weights.gt(0)
    if valid.any():
        return float((values[valid] * weights[valid]).sum() / weights[valid].sum())
    return float(values.mean())


def normalize_synergy_frame(
    frame: pd.DataFrame,
    player_index_frame: pd.DataFrame,
    *,
    season: str,
    play_type: str,
) -> pd.DataFrame:
    """Turn one response into a single row per player and play type."""

    _require_columns(frame, SYNERGY_COLUMNS, "SynergyPlayTypes")
    _require_columns(player_index_frame, PLAYER_INDEX_COLUMNS, "PlayerIndex")
    if play_type not in PLAY_TYPES:
        raise ValueError(f"Unsupported display play type: {play_type}")

    positions = player_index_frame[["PERSON_ID", "POSITION"]].copy()
    positions = positions.rename(
        columns={
            "PERSON_ID": "PLAYER_ID",
            "POSITION": "PLAYER_POSITION",
        }
    )
    positions = positions.drop_duplicates("PLAYER_ID", keep="last")

    source = frame.copy()
    source = source.merge(positions, how="left", on="PLAYER_ID", validate="many_to_one")
    for column in (
        "PERCENTILE",
        "POSS_PCT",
        "PPP",
        "TOV_POSS_PCT",
        "SCORE_POSS_PCT",
        "EFG_PCT",
        "POSS",
        "PTS",
        "FGA",
    ):
        source[column] = pd.to_numeric(source[column], errors="coerce")

    rows: list[dict[str, object]] = []
    for player_id, group in source.groupby("PLAYER_ID", sort=False, dropna=False):
        group = group.copy()
        possessions = float(group["POSS"].fillna(0).sum())
        if possessions <= 0:
            continue

        largest_stint = group.loc[group["POSS"].fillna(0).idxmax()]
        team_possessions = (
            group.assign(TEAM_ABBREVIATION=group["TEAM_ABBREVIATION"].astype(str))
            .groupby("TEAM_ABBREVIATION")["POSS"]
            .sum()
            .sort_values(ascending=False)
        )
        team = "/".join(team_possessions.index)
        raw_position = group["PLAYER_POSITION"].dropna()
        position = normalize_position(raw_position.iloc[0]) if not raw_position.empty else None
        if position is None:
            continue

        points = float(group["PTS"].fillna(0).sum())
        ppp = points / possessions if possessions else _weighted_average(group, "PPP", "POSS")
        rows.append(
            {
                "season": season,
                "player_id": int(player_id),
                "player": str(largest_stint["PLAYER_NAME"]),
                "team": team,
                "position": position,
                "play_type": play_type,
                "possessions": int(round(possessions)),
                "frequency": _weighted_average(group, "POSS_PCT", "POSS"),
                "ppp": round(ppp, 3),
                "efg_pct": round(_weighted_average(group, "EFG_PCT", "FGA") * 100, 1),
                "tov_pct": round(_weighted_average(group, "TOV_POSS_PCT", "POSS") * 100, 1),
                "score_pct": round(_weighted_average(group, "SCORE_POSS_PCT", "POSS") * 100, 1),
                "percentile": round(_weighted_average(group, "PERCENTILE", "POSS") * 100),
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError(f"SynergyPlayTypes returned no usable rows for {season} {play_type}")

    fallback = (result["ppp"].rank(method="average", pct=True) * 98 + 1).round()
    result["percentile"] = pd.to_numeric(result["percentile"], errors="coerce")
    result["percentile"] = result["percentile"].fillna(fallback).clip(1, 99).astype(int)
    return result


def _with_retries(
    request: Callable[[], T],
    *,
    label: str,
    attempts: int,
) -> T:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return request()
        except Exception as exc:  # nba_api may surface request failures through several exception types.
            last_error = exc
            if attempt == attempts:
                break
            wait_seconds = attempt * 2
            print(f"  {label} failed on attempt {attempt}; retrying in {wait_seconds}s")
            time.sleep(wait_seconds)
    raise RuntimeError(f"Unable to fetch {label} after {attempts} attempts") from last_error


def fetch_dataset(
    seasons: Iterable[str],
    *,
    timeout: int = 45,
    delay: float = 0.65,
    attempts: int = 3,
) -> pd.DataFrame:
    """Download PlayerIndex and Synergy data for the requested seasons."""

    collected: list[pd.DataFrame] = []
    seasons = tuple(seasons)
    for season_number, season in enumerate(seasons, start=1):
        print(f"Season {season} ({season_number}/{len(seasons)})")
        index_endpoint = _with_retries(
            lambda: playerindex.PlayerIndex(
                season=season,
                historical_nullable="1",
                timeout=timeout,
            ),
            label=f"PlayerIndex {season}",
            attempts=attempts,
        )
        index_frame = index_endpoint.player_index.get_data_frame()
        time.sleep(delay)

        for play_number, (label, parameter) in enumerate(
            PLAY_TYPE_PARAMETERS.items(), start=1
        ):
            print(f"  {play_number}/{len(PLAY_TYPE_PARAMETERS)} {label}")
            endpoint = _with_retries(
                lambda parameter=parameter: synergyplaytypes.SynergyPlayTypes(
                    player_or_team_abbreviation="P",
                    season=season,
                    season_type_all_star="Regular Season",
                    per_mode_simple="Totals",
                    play_type_nullable=parameter,
                    type_grouping_nullable="offensive",
                    timeout=timeout,
                ),
                label=f"SynergyPlayTypes {season} {label}",
                attempts=attempts,
            )
            raw = endpoint.synergy_play_type.get_data_frame()
            collected.append(
                normalize_synergy_frame(
                    raw,
                    index_frame,
                    season=season,
                    play_type=label,
                )
            )
            time.sleep(delay)

    dataset = pd.concat(collected, ignore_index=True)
    return validate_playtype_data(dataset, source="nba_api responses")


def write_cache(
    dataset: pd.DataFrame,
    *,
    output: Path,
    seasons: Iterable[str],
) -> Path:
    """Write the CSV and source metadata without leaving partial files."""

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".csv.tmp")
    dataset.to_csv(temporary, index=False, encoding="utf-8")
    temporary.replace(output)

    metadata = {
        "source": "NBA Stats via nba_api",
        "source_endpoint": "nba_api.stats.endpoints.SynergyPlayTypes",
        "position_endpoint": "nba_api.stats.endpoints.PlayerIndex",
        "nba_api_version": importlib.metadata.version("nba_api"),
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "season_type": "Regular Season",
        "seasons": list(seasons),
        "play_types": list(PLAY_TYPE_PARAMETERS),
        "rows": len(dataset),
    }
    metadata_path = output.with_suffix(".meta.json")
    metadata_temporary = metadata_path.with_suffix(".json.tmp")
    metadata_temporary.write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    metadata_temporary.replace(metadata_path)
    return output


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download NBA Synergy playtype data for Playtype Playground."
    )
    parser.add_argument("--seasons", nargs="+", default=list(DEFAULT_SEASONS))
    parser.add_argument("--output", type=Path, default=data_file)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--delay", type=float, default=0.65)
    parser.add_argument("--attempts", type=int, default=3)
    return parser


def main() -> None:
    args = _parser().parse_args()
    dataset = fetch_dataset(
        args.seasons,
        timeout=args.timeout,
        delay=args.delay,
        attempts=args.attempts,
    )
    cache = write_cache(dataset, output=args.output, seasons=args.seasons)
    print(f"Wrote {len(dataset):,} player play-type rows to {cache}")


if __name__ == "__main__":
    main()
