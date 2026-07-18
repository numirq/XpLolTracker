from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen


VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
ICON_URL = "https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{champion}.png"
USER_AGENT = "LoL-XP-Tracker-Champion-Icons/0.9"


class ChampionIconCache:
    """Small on-disk cache for official Riot Data Dragon champion squares."""

    def __init__(
        self,
        cache_directory: str | Path,
        opener: Callable = urlopen,
    ) -> None:
        self.cache_directory = Path(cache_directory)
        self.opener = opener
        self._version: str | None = None
        self._version_lock = threading.Lock()

    @staticmethod
    def champion_id(value: str) -> str:
        champion = str(value or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9]{1,40}", champion):
            raise ValueError("Nieprawidłowa nazwa bohatera.")
        return champion

    def latest_version(self) -> str:
        with self._version_lock:
            if self._version:
                return self._version
            version_file = self.cache_directory / "version.txt"
            cached = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else ""
            try:
                request = Request(VERSIONS_URL, headers={"User-Agent": USER_AGENT})
                with self.opener(request, timeout=8) as response:
                    payload = response.read(512_000)
                versions = json.loads(payload.decode("utf-8"))
                version = str(versions[0]) if isinstance(versions, list) and versions else ""
                if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}", version):
                    raise ValueError("Nieprawidłowa wersja Data Dragon.")
                self.cache_directory.mkdir(parents=True, exist_ok=True)
                version_file.write_text(version, encoding="utf-8")
                self._version = version
                return version
            except Exception:
                if re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}", cached):
                    self._version = cached
                    return cached
                raise

    def icon_path(self, champion_name: str) -> Path:
        champion = self.champion_id(champion_name)
        version = self.latest_version()
        directory = self.cache_directory / version
        destination = directory / f"{champion}.png"
        if destination.exists() and destination.stat().st_size > 100:
            return destination

        request = Request(
            ICON_URL.format(version=version, champion=champion),
            headers={"User-Agent": USER_AGENT},
        )
        with self.opener(request, timeout=8) as response:
            payload = response.read(2_000_000)
        if len(payload) < 100 or not payload.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Data Dragon nie zwrócił prawidłowej ikony PNG.")
        directory.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".tmp")
        temporary.write_bytes(payload)
        temporary.replace(destination)
        return destination
