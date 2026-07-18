import tempfile
import unittest
from pathlib import Path

from lol_tracker.database import Database
from lol_tracker.lcu_client import LcuClient
from lol_tracker.riot_api import RiotApiClient
from lol_tracker.updater import version_tuple
from lol_tracker.xp import (
    calculate_xp_gain,
    games_to_level_30,
    games_to_next_level,
    progress_percent,
    xp_to_level_30,
)


class XpTests(unittest.TestCase):
    def test_gain_on_same_level(self):
        self.assertEqual(calculate_xp_gain(24, 1601, 2500, 24, 1850), 249)

    def test_gain_on_level_up(self):
        self.assertEqual(calculate_xp_gain(24, 2400, 2500, 25, 150), 250)

    def test_unknown_when_multiple_levels(self):
        self.assertIsNone(calculate_xp_gain(1, 0, 100, 3, 10))

    def test_progress_and_estimate(self):
        self.assertEqual(progress_percent(50, 200), 25)
        self.assertEqual(games_to_next_level(1600, 2500, 300), 3)

    def test_progress_to_level_30(self):
        self.assertEqual(xp_to_level_30(29, 1000, 2688), 1688)
        self.assertEqual(xp_to_level_30(30, 0, 2688), 0)
        self.assertEqual(games_to_level_30(29, 1000, 2688, 200), 9)


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "test.db")
        self.account_id = self.db.add_account("TestPlayer", "EUW", "EUW1", 24, 1601, 2500)

    def tearDown(self):
        self.temp.cleanup()

    def test_accounts_are_independent(self):
        other = self.db.add_account("inna nazwa", "EUW", "EUW1", 10, 100, 500)
        self.db.add_game(
            self.account_id,
            {"champion": "Ahri", "xp_gained": 200, "level_after": 24, "xp_after": 1801, "xp_required_after": 2500},
        )
        self.assertEqual(len(self.db.list_games(self.account_id)), 1)
        self.assertEqual(len(self.db.list_games(other)), 0)

    def test_game_updates_progress(self):
        self.db.add_game(
            self.account_id,
            {"champion": "Jinx", "xp_gained": 300, "level_after": 24, "xp_after": 1901, "xp_required_after": 2500},
        )
        account = self.db.get_account(self.account_id)
        self.assertEqual(account["current_xp"], 1901)
        self.assertEqual(self.db.stats(self.account_id)["avg_xp"], 300)

    def test_existing_import_can_receive_xp_later(self):
        self.db.add_game(
            self.account_id,
            {
                "match_id": "EUW1_123", "champion": "Lux", "level_after": 24,
                "xp_after": 1601, "xp_required_after": 2500,
            },
        )
        self.db.update_match_progress(self.account_id, "EUW1_123", 24, 1850, 2500, 249)
        game = self.db.list_games(self.account_id)[0]
        self.assertEqual(game["xp_gained"], 249)
        self.assertEqual(self.db.get_account(self.account_id)["current_xp"], 1850)

    def test_champion_and_today_stats(self):
        self.db.add_game(
            self.account_id,
            {
                "champion": "Katarina", "win": False, "kills": 1, "deaths": 9,
                "assists": 0, "xp_gained": 137, "duration_seconds": 913,
                "level_after": 24, "xp_after": 1738, "xp_required_after": 2304,
            },
        )
        champion = self.db.champion_stats(self.account_id)[0]
        self.assertEqual(champion["games"], 1)
        self.assertEqual(champion["total_xp"], 137)
        self.assertEqual(self.db.stats_today(self.account_id)["games"], 1)

    def test_filters_and_activity_calendar(self):
        self.db.add_game(
            self.account_id,
            {
                "champion": "Lux", "queue_name": "ARAM", "win": True,
                "gold": 9000, "vision_score": 12, "champion_level": 16,
                "xp_gained": 200, "level_after": 24, "xp_after": 1801,
                "xp_required_after": 2304,
            },
        )
        self.assertEqual(len(self.db.list_games_filtered(self.account_id, search="lux")), 1)
        self.assertEqual(len(self.db.list_games_filtered(self.account_id, result="loss")), 0)
        now = __import__("datetime").datetime.now()
        activity = self.db.activity_for_month(self.account_id, now.year, now.month)
        self.assertEqual(sum(day["games"] for day in activity.values()), 1)

    def test_old_match_can_be_enriched_without_losing_xp(self):
        game_id = self.db.add_game(
            self.account_id,
            {
                "match_id": "EUW1_999", "champion": "Illaoi", "xp_gained": 250,
                "level_after": 24, "xp_after": 1988, "xp_required_after": 2304,
            },
        )
        self.db.enrich_game_details(
            game_id,
            self.account_id,
            {
                "played_at": "2026-07-18T17:11:00+02:00", "champion": "Illaoi",
                "queue_name": "Normal Draft", "role": "UTILITY", "win": False,
                "kills": 2, "deaths": 13, "assists": 2, "cs": 56, "damage": 14032,
                "gold": 9123, "vision_score": 18, "champion_level": 15,
                "duration_seconds": 1794,
            },
        )
        game = self.db.get_game(game_id, self.account_id)
        self.assertEqual(game["gold"], 9123)
        self.assertEqual(game["vision_score"], 18)
        self.assertEqual(game["xp_gained"], 250)
        self.assertEqual(game["xp_after"], 1988)


class RiotParserTests(unittest.TestCase):
    def test_parse_match(self):
        payload = {
            "metadata": {"matchId": "EUW1_123"},
            "info": {
                "gameCreation": 1_700_000_000_000,
                "gameDuration": 1800,
                "queueId": 420,
                "participants": [{
                    "puuid": "p1", "championName": "Lux", "win": True,
                    "kills": 5, "deaths": 2, "assists": 9,
                    "totalMinionsKilled": 150, "neutralMinionsKilled": 10,
                    "totalDamageDealtToChampions": 21000, "teamPosition": "MIDDLE",
                    "goldEarned": 12345, "visionScore": 18, "champLevel": 17,
                }],
            },
        }
        parsed = RiotApiClient.parse_match(payload, "p1")
        self.assertEqual(parsed["champion"], "Lux")
        self.assertEqual(parsed["cs"], 160)
        self.assertEqual(parsed["queue_name"], "Ranked Solo/Duo")
        self.assertEqual(parsed["gold"], 12345)


class LcuParserTests(unittest.TestCase):
    def test_xp_until_next_level_is_full_bar_size(self):
        client = object.__new__(LcuClient)
        client._get = lambda _path: {
            "gameName": "TestPlayer",
            "tagLine": "EUW",
            "summonerLevel": 24,
            "xpSinceLastLevel": 1738,
            "xpUntilNextLevel": 2304,
            "puuid": "p1",
        }
        snapshot = client.current_summoner()
        self.assertEqual(snapshot["xp"], 1738)
        self.assertEqual(snapshot["xp_required"], 2304)


class UpdaterTests(unittest.TestCase):
    def test_semantic_version_comparison(self):
        self.assertGreater(version_tuple("0.5.0"), version_tuple("0.4.9"))
        self.assertEqual(version_tuple("v1.2.3"), (1, 2, 3))


if __name__ == "__main__":
    unittest.main()
