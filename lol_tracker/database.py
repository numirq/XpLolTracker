from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_name TEXT NOT NULL,
    tag_line TEXT NOT NULL,
    platform TEXT NOT NULL,
    current_level INTEGER NOT NULL DEFAULT 1,
    current_xp INTEGER NOT NULL DEFAULT 0,
    xp_required INTEGER NOT NULL DEFAULT 0,
    goal_level INTEGER NOT NULL DEFAULT 30,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(game_name COLLATE NOCASE, tag_line COLLATE NOCASE, platform COLLATE NOCASE)
);

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    match_id TEXT,
    played_at TEXT NOT NULL,
    champion TEXT NOT NULL,
    queue_name TEXT NOT NULL DEFAULT 'Nieznany',
    role TEXT NOT NULL DEFAULT '',
    win INTEGER,
    kills INTEGER NOT NULL DEFAULT 0,
    deaths INTEGER NOT NULL DEFAULT 0,
    assists INTEGER NOT NULL DEFAULT 0,
    cs INTEGER NOT NULL DEFAULT 0,
    damage INTEGER NOT NULL DEFAULT 0,
    gold INTEGER NOT NULL DEFAULT 0,
    vision_score INTEGER NOT NULL DEFAULT 0,
    champion_level INTEGER NOT NULL DEFAULT 0,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    xp_gained INTEGER,
    level_after INTEGER NOT NULL,
    xp_after INTEGER NOT NULL,
    xp_required_after INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'manual',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(account_id, match_id)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(games)")}
            migrations = {
                "gold": "INTEGER NOT NULL DEFAULT 0",
                "vision_score": "INTEGER NOT NULL DEFAULT 0",
                "champion_level": "INTEGER NOT NULL DEFAULT 0",
            }
            for name, definition in migrations.items():
                if name not in columns:
                    connection.execute(f"ALTER TABLE games ADD COLUMN {name} {definition}")
            account_columns = {row[1] for row in connection.execute("PRAGMA table_info(accounts)")}
            if "goal_level" not in account_columns:
                connection.execute(
                    "ALTER TABLE accounts ADD COLUMN goal_level INTEGER NOT NULL DEFAULT 30"
                )

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def add_account(
        self,
        game_name: str,
        tag_line: str,
        platform: str,
        level: int,
        xp: int,
        xp_required: int,
    ) -> int:
        now = self._now()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO accounts
                    (game_name, tag_line, platform, current_level, current_xp,
                     xp_required, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_name.strip(),
                    tag_line.strip(),
                    platform.upper(),
                    int(level),
                    int(xp),
                    int(xp_required),
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def list_accounts(self) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    "SELECT * FROM accounts ORDER BY game_name COLLATE NOCASE, tag_line COLLATE NOCASE"
                )
            )

    def get_account(self, account_id: int) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()

    def find_account(self, game_name: str, tag_line: str) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT * FROM accounts
                WHERE game_name = ? COLLATE NOCASE AND tag_line = ? COLLATE NOCASE
                ORDER BY id LIMIT 1
                """,
                (game_name, tag_line),
            ).fetchone()

    def update_account_progress(
        self, account_id: int, level: int, xp: int, xp_required: int
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE accounts
                SET current_level = ?, current_xp = ?, xp_required = ?, updated_at = ?
                WHERE id = ?
                """,
                (int(level), int(xp), int(xp_required), self._now(), account_id),
            )

    def update_account_goal(self, account_id: int, goal_level: int) -> None:
        goal_level = int(goal_level)
        if goal_level < 2:
            raise ValueError("Cel musi wynosić co najmniej poziom 2.")
        with self.connect() as connection:
            connection.execute(
                "UPDATE accounts SET goal_level = ?, updated_at = ? WHERE id = ?",
                (goal_level, self._now(), account_id),
            )

    def update_account_identity(
        self, account_id: int, game_name: str, tag_line: str, platform: str
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE accounts SET game_name = ?, tag_line = ?, platform = ?, updated_at = ?
                WHERE id = ?
                """,
                (game_name.strip(), tag_line.strip(), platform.upper(), self._now(), account_id),
            )

    def delete_account(self, account_id: int) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM accounts WHERE id = ?", (account_id,))

    def add_game(self, account_id: int, data: dict[str, Any]) -> int:
        account = self.get_account(account_id)
        if account is None:
            raise ValueError("Nie znaleziono konta")

        fields = {
            "match_id": data.get("match_id") or None,
            "played_at": data.get("played_at") or self._now(),
            "champion": data.get("champion") or "Nieznany",
            "queue_name": data.get("queue_name") or "Nieznany",
            "role": data.get("role") or "",
            "win": None if data.get("win") is None else int(bool(data.get("win"))),
            "kills": int(data.get("kills") or 0),
            "deaths": int(data.get("deaths") or 0),
            "assists": int(data.get("assists") or 0),
            "cs": int(data.get("cs") or 0),
            "damage": int(data.get("damage") or 0),
            "gold": int(data.get("gold") or 0),
            "vision_score": int(data.get("vision_score") or 0),
            "champion_level": int(data.get("champion_level") or 0),
            "duration_seconds": int(data.get("duration_seconds") or 0),
            "xp_gained": None if data.get("xp_gained") in (None, "") else int(data["xp_gained"]),
            "level_after": int(data.get("level_after", account["current_level"])),
            "xp_after": int(data.get("xp_after", account["current_xp"])),
            "xp_required_after": int(data.get("xp_required_after", account["xp_required"])),
            "source": data.get("source") or "manual",
            "notes": data.get("notes") or "",
        }

        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO games (
                    account_id, match_id, played_at, champion, queue_name, role, win,
                    kills, deaths, assists, cs, damage, gold, vision_score, champion_level,
                    duration_seconds, xp_gained,
                    level_after, xp_after, xp_required_after, source, notes, created_at
                ) VALUES (
                    :account_id, :match_id, :played_at, :champion, :queue_name, :role, :win,
                    :kills, :deaths, :assists, :cs, :damage, :gold, :vision_score, :champion_level,
                    :duration_seconds, :xp_gained,
                    :level_after, :xp_after, :xp_required_after, :source, :notes, :created_at
                )
                """,
                {"account_id": account_id, "created_at": self._now(), **fields},
            )
            connection.execute(
                """
                UPDATE accounts SET current_level = ?, current_xp = ?, xp_required = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    fields["level_after"],
                    fields["xp_after"],
                    fields["xp_required_after"],
                    self._now(),
                    account_id,
                ),
            )
            return int(cursor.lastrowid)

    def update_game(self, game_id: int, account_id: int, data: dict[str, Any]) -> None:
        fields = {
            "played_at": data["played_at"],
            "champion": data["champion"],
            "queue_name": data["queue_name"],
            "role": data.get("role", ""),
            "win": None if data.get("win") is None else int(bool(data["win"])),
            "kills": int(data.get("kills", 0)),
            "deaths": int(data.get("deaths", 0)),
            "assists": int(data.get("assists", 0)),
            "cs": int(data.get("cs", 0)),
            "damage": int(data.get("damage", 0)),
            "gold": int(data.get("gold", 0)),
            "vision_score": int(data.get("vision_score", 0)),
            "champion_level": int(data.get("champion_level", 0)),
            "duration_seconds": int(data.get("duration_seconds", 0)),
            "xp_gained": None if data.get("xp_gained") in (None, "") else int(data["xp_gained"]),
            "level_after": int(data["level_after"]),
            "xp_after": int(data["xp_after"]),
            "xp_required_after": int(data.get("xp_required_after", 0)),
            "notes": data.get("notes", ""),
        }
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE games SET
                    played_at=:played_at, champion=:champion, queue_name=:queue_name,
                    role=:role, win=:win, kills=:kills, deaths=:deaths, assists=:assists,
                    cs=:cs, damage=:damage, gold=:gold, vision_score=:vision_score,
                    champion_level=:champion_level, duration_seconds=:duration_seconds,
                    xp_gained=:xp_gained, level_after=:level_after, xp_after=:xp_after,
                    xp_required_after=:xp_required_after, notes=:notes
                WHERE id=:game_id AND account_id=:account_id
                """,
                {"game_id": game_id, "account_id": account_id, **fields},
            )

    def delete_game(self, game_id: int, account_id: int) -> None:
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM games WHERE id = ? AND account_id = ?", (game_id, account_id)
            )
        self.recalculate_account(account_id)

    def recalculate_account(self, account_id: int) -> None:
        with self.connect() as connection:
            latest = connection.execute(
                """
                SELECT level_after, xp_after, xp_required_after FROM games
                WHERE account_id = ? ORDER BY played_at DESC, id DESC LIMIT 1
                """,
                (account_id,),
            ).fetchone()
            if latest:
                connection.execute(
                    """
                    UPDATE accounts SET current_level=?, current_xp=?, xp_required=?, updated_at=?
                    WHERE id=?
                    """,
                    (*latest, self._now(), account_id),
                )

    def list_games(self, account_id: int, limit: int = 500) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    """
                    SELECT * FROM games WHERE account_id = ?
                    ORDER BY played_at DESC, id DESC LIMIT ?
                    """,
                    (account_id, limit),
                )
            )

    def list_games_filtered(
        self,
        account_id: int,
        search: str = "",
        result: str = "all",
        queue_name: str = "all",
        date_scope: str = "all",
        limit: int = 500,
    ) -> list[sqlite3.Row]:
        clauses = ["account_id = ?"]
        params: list[Any] = [account_id]
        if search.strip():
            clauses.append("(champion LIKE ? COLLATE NOCASE OR notes LIKE ? COLLATE NOCASE)")
            term = f"%{search.strip()}%"
            params.extend([term, term])
        if result == "win":
            clauses.append("win = 1")
        elif result == "loss":
            clauses.append("win = 0")
        if queue_name != "all":
            clauses.append("queue_name = ?")
            params.append(queue_name)
        if date_scope == "today":
            clauses.append("date(played_at, 'localtime') = date('now', 'localtime')")
        elif date_scope == "7d":
            clauses.append("datetime(played_at) >= datetime('now', '-7 days')")
        elif date_scope == "30d":
            clauses.append("datetime(played_at) >= datetime('now', '-30 days')")
        params.append(limit)
        query = (
            "SELECT * FROM games WHERE " + " AND ".join(clauses)
            + " ORDER BY played_at DESC, id DESC LIMIT ?"
        )
        with self.connect() as connection:
            return list(connection.execute(query, params))

    def queue_names(self, account_id: int) -> list[str]:
        with self.connect() as connection:
            return [
                row[0]
                for row in connection.execute(
                    """
                    SELECT DISTINCT queue_name FROM games WHERE account_id = ?
                    ORDER BY queue_name COLLATE NOCASE
                    """,
                    (account_id,),
                )
                if row[0]
            ]

    def get_game(self, game_id: int, account_id: int) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM games WHERE id = ? AND account_id = ?", (game_id, account_id)
            ).fetchone()

    def match_exists(self, account_id: int, match_id: str) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM games WHERE account_id = ? AND match_id = ?",
                (account_id, match_id),
            ).fetchone()
            return row is not None

    def update_match_progress(
        self,
        account_id: int,
        match_id: str,
        level: int,
        xp: int,
        xp_required: int,
        xp_gained: int | None,
    ) -> None:
        """Attach an XP snapshot when a match was imported before client sync."""
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE games SET level_after=?, xp_after=?, xp_required_after=?, xp_gained=?
                WHERE account_id=? AND match_id=?
                """,
                (level, xp, xp_required, xp_gained, account_id, match_id),
            )
            connection.execute(
                """
                UPDATE accounts SET current_level=?, current_xp=?, xp_required=?, updated_at=?
                WHERE id=?
                """,
                (level, xp, xp_required, self._now(), account_id),
            )

    def enrich_game_details(self, game_id: int, account_id: int, data: dict[str, Any]) -> None:
        """Refresh match statistics without touching the saved account-XP snapshot."""
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE games SET
                    played_at=?, champion=?, queue_name=?, role=?, win=?, kills=?, deaths=?,
                    assists=?, cs=?, damage=?, gold=?, vision_score=?, champion_level=?,
                    duration_seconds=?
                WHERE id=? AND account_id=?
                """,
                (
                    data.get("played_at") or self._now(),
                    data.get("champion") or "Nieznany",
                    data.get("queue_name") or "Nieznany",
                    data.get("role") or "",
                    None if data.get("win") is None else int(bool(data.get("win"))),
                    int(data.get("kills") or 0),
                    int(data.get("deaths") or 0),
                    int(data.get("assists") or 0),
                    int(data.get("cs") or 0),
                    int(data.get("damage") or 0),
                    int(data.get("gold") or 0),
                    int(data.get("vision_score") or 0),
                    int(data.get("champion_level") or 0),
                    int(data.get("duration_seconds") or 0),
                    game_id,
                    account_id,
                ),
            )

    def stats(self, account_id: int) -> dict[str, float | int | None]:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS games,
                       COALESCE(SUM(xp_gained), 0) AS total_xp,
                       AVG(xp_gained) AS avg_xp,
                       SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) AS wins,
                       SUM(CASE WHEN win IS NOT NULL THEN 1 ELSE 0 END) AS decided,
                       COALESCE(SUM(duration_seconds), 0) AS duration_seconds
                FROM games WHERE account_id = ?
                """,
                (account_id,),
            ).fetchone()
        return dict(row) if row else {"games": 0, "total_xp": 0, "avg_xp": None, "wins": 0, "decided": 0}

    def stats_today(self, account_id: int) -> dict[str, float | int | None]:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS games,
                       COALESCE(SUM(xp_gained), 0) AS total_xp,
                       AVG(xp_gained) AS avg_xp,
                       SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) AS wins,
                       SUM(CASE WHEN win IS NOT NULL THEN 1 ELSE 0 END) AS decided,
                       COALESCE(SUM(duration_seconds), 0) AS duration_seconds
                FROM games
                WHERE account_id = ? AND date(played_at, 'localtime') = date('now', 'localtime')
                """,
                (account_id,),
            ).fetchone()
        return dict(row)

    def stats_created_since(self, account_id: int, since: str) -> dict[str, float | int | None]:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS games,
                       COALESCE(SUM(xp_gained), 0) AS total_xp,
                       AVG(xp_gained) AS avg_xp,
                       SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) AS wins,
                       SUM(CASE WHEN win IS NOT NULL THEN 1 ELSE 0 END) AS decided,
                       COALESCE(SUM(duration_seconds), 0) AS duration_seconds
                FROM games WHERE account_id = ? AND created_at >= ?
                """,
                (account_id, since),
            ).fetchone()
        return dict(row)

    def champion_stats(self, account_id: int) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    """
                    SELECT champion,
                           COUNT(*) AS games,
                           SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) AS wins,
                           SUM(CASE WHEN win IS NOT NULL THEN 1 ELSE 0 END) AS decided,
                           SUM(kills) AS kills,
                           SUM(deaths) AS deaths,
                           SUM(assists) AS assists,
                           AVG(xp_gained) AS avg_xp,
                           COALESCE(SUM(xp_gained), 0) AS total_xp,
                           COALESCE(SUM(duration_seconds), 0) AS duration_seconds
                    FROM games WHERE account_id = ?
                    GROUP BY champion COLLATE NOCASE
                    ORDER BY games DESC, champion COLLATE NOCASE
                    """,
                    (account_id,),
                )
            )

    def activity_for_month(self, account_id: int, year: int, month: int) -> dict[str, dict[str, int]]:
        prefix = f"{year:04d}-{month:02d}"
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT substr(played_at, 1, 10) AS day,
                       COUNT(*) AS games,
                       COALESCE(SUM(xp_gained), 0) AS xp,
                       SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) AS wins
                FROM games
                WHERE account_id = ? AND substr(played_at, 1, 7) = ?
                GROUP BY substr(played_at, 1, 10)
                """,
                (account_id, prefix),
            )
            return {
                row["day"]: {"games": int(row["games"]), "xp": int(row["xp"]), "wins": int(row["wins"] or 0)}
                for row in rows
            }

    def get_setting(self, key: str, default: str = "") -> str:
        with self.connect() as connection:
            row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO settings(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
