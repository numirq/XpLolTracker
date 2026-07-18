from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from . import __version__


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
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        *,
        code: str = "api_error",
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def parse_backend_invitation(value: str) -> dict[str, str]:
    invitation = value.strip()
    prefix = "LOLXP1."
    if not invitation.startswith(prefix):
        raise RiotApiError(
            "To nie jest prawidłowe zaproszenie LoL XP Tracker.",
            code="invalid_invitation",
        )
    encoded = invitation[len(prefix) :]
    try:
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RiotApiError(
            "Zaproszenie jest uszkodzone albo niepełne.",
            code="invalid_invitation",
        ) from error
    if not isinstance(payload, dict):
        raise RiotApiError("Zaproszenie ma nieprawidłowy format.", code="invalid_invitation")
    server = str(payload.get("server") or "").strip().rstrip("/")
    token = str(payload.get("token") or "").strip()
    parsed = urlparse(server)
    if parsed.scheme != "https" or not parsed.netloc or len(token) < 24 or len(token) > 256:
        raise RiotApiError("Zaproszenie ma nieprawidłowe dane.", code="invalid_invitation")
    return {"server": server, "token": token}


class RiotApiClient:
    def __init__(
        self,
        api_key: str,
        platform: str,
        *,
        backend_url: str = "",
        access_token: str = "",
        client_instance_id: str = "",
    ):
        self.api_key = api_key.strip()
        self.platform = platform.upper()
        self.region = REGIONAL_ROUTES.get(self.platform, "europe")
        self.backend_url = backend_url.strip().rstrip("/")
        self.access_token = access_token.strip()
        self.client_instance_id = client_instance_id.strip()
        if self.backend_url:
            parsed = urlparse(self.backend_url)
            if parsed.scheme != "https" or not parsed.netloc:
                raise RiotApiError(
                    "Adres prywatnego serwera musi rozpoczynać się od https://",
                    code="configuration_error",
                )
            if not self.access_token:
                raise RiotApiError(
                    "Wpisz kod dostępu do prywatnego serwera.",
                    code="configuration_error",
                )
        elif not self.api_key:
            raise RiotApiError(
                "Skonfiguruj prywatny serwer albo lokalny klucz Riot API.",
                code="configuration_error",
            )

    def _get(self, url: str) -> Any:
        request = Request(
            url,
            headers={"X-Riot-Token": self.api_key, "User-Agent": f"LoL-XP-Tracker/{__version__}"},
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
                code="riot_key_expired" if error.code in (401, 403) else "riot_api_error",
            ) from error
        except (URLError, TimeoutError) as error:
            raise RiotApiError("Nie udało się połączyć z API Riot.") from error

    def _get_backend(self, path: str, parameters: dict[str, str]) -> Any:
        url = f"{self.backend_url}{path}?{urlencode(parameters)}"
        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
                "User-Agent": f"LoL-XP-Tracker/{__version__}",
                "X-Tracker-Version": __version__,
                "X-Client-Instance": self.client_instance_id,
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            payload: dict[str, Any] = {}
            try:
                payload = json.loads(error.read().decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
            backend_error = payload.get("error") if isinstance(payload, dict) else None
            error_code = (
                str(backend_error.get("code") or "backend_error")
                if isinstance(backend_error, dict)
                else "backend_error"
            )
            default_messages = {
                401: "Kod dostępu do prywatnego serwera jest nieprawidłowy.",
                403: "Ten kod nie ma dostępu do wybranego konta Riot.",
                404: "Nie znaleziono konta lub meczu.",
                429: "Wysłano zbyt wiele zapytań. Spróbuj za chwilę.",
                503: "Klucz Riot na prywatnym serwerze wymaga wymiany przez właściciela.",
            }
            message = (
                str(backend_error.get("message"))
                if isinstance(backend_error, dict) and backend_error.get("message")
                else default_messages.get(error.code, f"Prywatny serwer zwrócił błąd {error.code}.")
            )
            raise RiotApiError(message, status_code=error.code, code=error_code) from error
        except (URLError, TimeoutError) as error:
            raise RiotApiError(
                "Nie udało się połączyć z prywatnym serwerem trackera.",
                code="backend_unavailable",
            ) from error

    @staticmethod
    def _parse_backend_match(data: dict[str, Any]) -> dict[str, Any]:
        queue_id = int(data.get("queue_id") or 0)
        return {
            "match_id": data.get("match_id"),
            "played_at": data.get("played_at")
            or datetime.now().astimezone().isoformat(timespec="seconds"),
            "champion": data.get("champion") or "Nieznany",
            "queue_name": QUEUE_NAMES.get(queue_id, f"Kolejka {queue_id}"),
            "role": data.get("role") or "",
            "win": bool(data.get("win")),
            "kills": int(data.get("kills") or 0),
            "deaths": int(data.get("deaths") or 0),
            "assists": int(data.get("assists") or 0),
            "cs": int(data.get("cs") or 0),
            "damage": int(data.get("damage") or 0),
            "gold": int(data.get("gold") or 0),
            "vision_score": int(data.get("vision_score") or 0),
            "champion_level": int(data.get("champion_level") or 0),
            "duration_seconds": int(data.get("duration_seconds") or 0),
            "source": "private_backend",
        }

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
        if self.backend_url:
            data = self._get_backend(
                "/v1/latest-match",
                {
                    "game_name": game_name,
                    "tag_line": tag_line,
                    "platform": self.platform,
                },
            )
            return self._parse_backend_match(data)
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
        if self.backend_url:
            data = self._get_backend(
                f"/v1/matches/{quote(match_id, safe='')}",
                {
                    "game_name": game_name,
                    "tag_line": tag_line,
                    "platform": self.platform,
                },
            )
            return self._parse_backend_match(data)
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
