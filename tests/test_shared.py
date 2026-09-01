from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "playtype_playground"))

from data_contract import REQUIRED_COLUMNS, validate_playtype_data  # noqa: E402
from fetch_nba_data import normalize_synergy_frame  # noqa: E402


def synergy_fixture() -> pd.DataFrame:
    base = {
        "PLAYER_ID": 7,
        "PLAYER_NAME": "Test Player",
        "PERCENTILE": 0.8,
        "POSS_PCT": 0.2,
        "PPP": 1.1,
        "TOV_POSS_PCT": 0.1,
        "SCORE_POSS_PCT": 0.5,
        "EFG_PCT": 0.55,
    }
    return pd.DataFrame(
        [
            {
                **base,
                "TEAM_ABBREVIATION": "AAA",
                "POSS": 60,
                "PTS": 66,
                "FGA": 40,
            },
            {
                **base,
                "TEAM_ABBREVIATION": "BBB",
                "POSS": 40,
                "PTS": 48,
                "FGA": 30,
                "POSS_PCT": 0.3,
                "PPP": 1.2,
                "EFG_PCT": 0.6,
            },
        ]
    )


class NbaApiDataTests(unittest.TestCase):
    def test_traded_player_stints_are_consolidated(self) -> None:
        player_index = pd.DataFrame(
            [{"PERSON_ID": 7, "TEAM_ABBREVIATION": "BBB", "POSITION": "G-F"}]
        )
        result = normalize_synergy_frame(
            synergy_fixture(),
            player_index,
            season="2025-26",
            play_type="Isolation",
        )

        self.assertEqual(len(result), 1)
        row = result.iloc[0]
        self.assertEqual(row["team"], "AAA/BBB")
        self.assertEqual(row["player_id"], 7)
        self.assertEqual(row["position"], "G")
        self.assertEqual(row["possessions"], 100)
        self.assertAlmostEqual(row["frequency"], 0.24)
        self.assertAlmostEqual(row["ppp"], 1.14)
        self.assertAlmostEqual(row["efg_pct"], 57.1)

    def test_normalized_output_satisfies_dashboard_contract(self) -> None:
        player_index = pd.DataFrame(
            [{"PERSON_ID": 7, "TEAM_ABBREVIATION": "BBB", "POSITION": "G"}]
        )
        result = normalize_synergy_frame(
            synergy_fixture(),
            player_index,
            season="2025-26",
            play_type="Isolation",
        )
        validated = validate_playtype_data(result, source="fixture")

        self.assertTrue(REQUIRED_COLUMNS.issubset(validated.columns))
        self.assertTrue(validated["frequency"].between(0, 1).all())
        self.assertTrue(validated["percentile"].between(1, 99).all())

    def test_contract_rejects_duplicate_player_rows(self) -> None:
        player_index = pd.DataFrame(
            [{"PERSON_ID": 7, "TEAM_ABBREVIATION": "BBB", "POSITION": "G"}]
        )
        result = normalize_synergy_frame(
            synergy_fixture(),
            player_index,
            season="2025-26",
            play_type="Isolation",
        )

        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_playtype_data(pd.concat([result, result]), source="fixture")


if __name__ == "__main__":
    unittest.main()
