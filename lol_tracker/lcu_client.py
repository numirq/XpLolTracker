from __future__ import annotations

import base64
import json
import re
import ssl
import subprocess
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LcuError(RuntimeError):
    pass


@dataclass(frozen=True)
class LcuCredentials:
    port: int
    token: str


class LcuClient:
    @staticmethod
    def discover() -> LcuCredentials:
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-CimInstance Win32_Process -Filter \"Name='LeagueClientUx.exe'\" | "
            "Select-Object -First 1 -ExpandProperty CommandLine)",
        ]
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=8, creationflags=0x08000000
            )
        except (FileNotFoundError, subprocess.SubprocessError) as error:
            raise LcuError("Nie udało się sprawdzić procesu klienta League of Legends.") from error

        command_line = result.stdout.strip()
        if not command_line:
            raise LcuError("Uruchom klienta League of Legends i zaloguj się na konto.")

        port_match = re.search(r"--app-port[= ](\d+)", command_line)
        token_match = re.search(r"--remoting-auth-token[= ]([^\s\"]+)", command_line)
        if not port_match or not token_match:
            raise LcuError("Klient działa, ale nie udało się odczytać połączenia lokalnego.")
        return LcuCredentials(int(port_match.group(1)), token_match.group(1))

    def __init__(self, credentials: LcuCredentials | None = None):
        self.credentials = credentials or self.discover()
        self.context = ssl.create_default_context()
        self.context.check_hostname = False
        self.context.verify_mode = ssl.CERT_NONE

    def _get(self, path: str) -> Any:
        auth = base64.b64encode(f"riot:{self.credentials.token}".encode()).decode()
        request = Request(
            f"https://127.0.0.1:{self.credentials.port}{path}",
            headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
        )
        try:
            with urlopen(request, timeout=5, context=self.context) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload) if payload else None
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise LcuError("Klient LoL nie odpowiedział. Spróbuj ponownie po zalogowaniu.") from error

    def current_summoner(self) -> dict[str, Any]:
        data = self._get("/lol-summoner/v1/current-summoner")
        if not isinstance(data, dict):
            raise LcuError("Nie udało się odczytać zalogowanego konta.")
        xp = int(data.get("xpSinceLastLevel") or 0)
        required = int(data.get("xpUntilNextLevel") or 0)
        game_name = data.get("gameName") or data.get("displayName") or ""
        tag_line = data.get("tagLine") or ""
        platform = ""
        try:
            region_data = self._get("/riotclient/region-locale")
            region = str(region_data.get("region") or "").upper() if isinstance(region_data, dict) else ""
            platform = {
                "EUW": "EUW1", "EUNE": "EUN1", "EUN": "EUN1", "NA": "NA1",
                "BR": "BR1", "TR": "TR1", "RU": "RU", "KR": "KR", "JP": "JP1",
                "LA1": "LA1", "LA2": "LA2", "OC": "OC1",
            }.get(region, "")
        except LcuError:
            pass
        return {
            "game_name": game_name,
            "tag_line": tag_line,
            "level": int(data.get("summonerLevel") or 1),
            "xp": xp,
            # Despite its name, xpUntilNextLevel is the full size of the
            # current level bar, not the amount remaining from this moment.
            "xp_required": required,
            "puuid": data.get("puuid") or "",
            "platform": platform,
        }
