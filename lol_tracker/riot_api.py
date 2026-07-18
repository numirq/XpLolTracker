from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


REGIONAL_ROUTES = {
    "EUW1": "europe",
    "EUN1": "europe",
    "TR1": "europe",
    "RU": "europe",
    "NA1": "americas",
    "BR1": "americas",
    "LA1": "americas",
    "LA2": "americas",
    "KR": "asia",
    "JP1": "asia",
    "OC1": "sea",
    "PH2": "sea",
    "SG2": "sea",
    "TH2": "sea",
    "TW2": "sea",
    "VN2": "sea",
}

QUEUE_NAMES = {
    0: "Niestandardowa",
    400: "Normal Draft",
    420: "Ranked Solo/Duo",
    430: "Normal Blind",
    440: "Ranked Flex",
    450: "ARAM",
    490: "Quickplay",
    700: "Clash",
    830: "Co-op vs AI Intro",
    840: "Co-op vs AI Beginner",
    850: "Co-op vs AI Intermediate",
    1700: "Arena",
}


class RiotApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class RiotApiClient:
    def __init__(self, api_key: str, platform: str):
        if not api_key.strip():
            raise RiotApiError("Najpierw wpisz klucz API Riot w ustawieniach.")
        self.api_key = api_key.strip()
        self.platform = platform.upper()
        self.region = REGIONAL_ROUTES.get(self.platform, "europe")

    def _get(self, url: str) -> Any:
        request = Request(
            url,
            headers={"X-Riot-Token": self.api_key, "User-Agent": "LoL-XP-Tracker/0.1"},
        )
        try:
            with urlopen(request, timeout=12) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            messages = {
                401: "Klucz API jest nieprawidłowy.",
                403: "Klucz API wygasł albo nie ma dostępu.",
                404: "Nie znaleziono konta lub meczu.",
                429: "Przekroczono limit zapytań API. Spróbuj za chwilę.",
            }
            raise RiotApiError(
                messages.get(error.code, f"API Riot zwróciło błąd {error.code}."),
                status_code=error.code,
            ) from error
        except (URLError, TimeoutError) as error:
            raise RiotApiError("Nie udało się połączyć z API Riot.") from error

    def resolve_account(self, game_name: str, tag_line: str) -> dict[str, Any]:
        return self._get(
            f"https://{self.region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/"
            f"{quote(game_name, safe='')}/{quote(tag_line, safe='')}"
        )

    def summoner(self, puuid: str) -> dict[str, Any]:
        return self._get(
            f"https://{self.platform.lower()}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/"
            f"{quote(puuid, safe='')}"
        )

    def latest_match(self, game_name: str, tag_line: str) -> dict[str, Any]:
        account = self.resolve_account(game_name, tag_line)
        puuid = account["puuid"]
        match_ids = self._get(
            f"https://{self.region}.api.riotgames.com/lol/match/v5/matches/by-puuid/"
            f"{quote(puuid, safe='')}/ids?start=0&count=1"
        )
        if not match_ids:
            raise RiotApiError("To konto nie ma dostępnych meczów w historii.")
        match_id = match_ids[0]
        return self.match_by_id(game_name, tag_line, match_id, puuid=puuid)

    def match_by_id(
        self,
        game_name: str,
        tag_line: str,
        match_id: str,
        *,
        puuid: str | None = None,
    ) -> dict[str, Any]:
        if puuid is None:
            puuid = self.resolve_account(game_name, tag_line)["puuid"]
        match = self._get(
            f"https://{self.region}.api.riotgames.com/lol/match/v5/matches/{quote(match_id, safe='')}"
        )
        return self.parse_match(match, puuid)

    @staticmethod
    def parse_match(match: dict[str, Any], puuid: str) -> dict[str, Any]:
        info = match.get("info", {})
        participant = next(
            (p for p in info.get("participants", []) if p.get("puuid") == puuid), None
        )
        if not participant:
            raise RiotApiError("Nie znaleziono gracza w danych meczu.")

        timestamp = int(info.get("gameCreation") or 0) / 1000
        played_at = (
            datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")
            if timestamp
            else datetime.now().astimezone().isoformat(timespec="seconds")
        )
        queue_id = int(info.get("queueId") or 0)
        return {
            "match_id": match.get("metadata", {}).get("matchId"),
            "played_at": played_at,
            "champion": participant.get("championName") or "Nieznany",
            "queue_name": QUEUE_NAMES.get(queue_id, f"Kolejka {queue_id}"),
            "role": participant.get("teamPosition") or participant.get("role") or "",
            "win": bool(participant.get("win")),
            "kills": int(participant.get("kills") or 0),
            "deaths": int(participant.get("deaths") or 0),
            "assists": int(participant.get("assists") or 0),
            "cs": int(participant.get("totalMinionsKilled") or 0)
            + int(participant.get("neutralMinionsKilled") or 0),
            "damage": int(participant.get("totalDamageDealtToChampions") or 0),
            "gold": int(participant.get("goldEarned") or 0),
            "vision_score": int(participant.get("visionScore") or 0),
            "champion_level": int(participant.get("champLevel") or 0),
            "duration_seconds": int(info.get("gameDuration") or 0),
            "source": "riot_api",
        }
