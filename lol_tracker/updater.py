from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_MANIFEST_URL = (
    "https://raw.githubusercontent.com/numirq/XpLolTracker/main/update-manifest.json"
)


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    download_url: str
    sha256: str
    notes: str = ""


def version_tuple(version: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in version.strip().lstrip("v").split("."))
    except ValueError as error:
        raise UpdateError("Źródło aktualizacji podało nieprawidłowy numer wersji.") from error


def check_for_update(manifest_url: str, current_version: str) -> UpdateInfo | None:
    if not manifest_url.strip():
        raise UpdateError("Nie ustawiono adresu źródła aktualizacji.")
    if urlparse(manifest_url).scheme != "https":
        raise UpdateError("Adres aktualizacji musi rozpoczynać się od https://")
    request = Request(manifest_url.strip(), headers={"User-Agent": "LoL-XP-Tracker-Updater"})
    try:
        with urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise UpdateError("Nie udało się sprawdzić dostępności aktualizacji.") from error
    try:
        info = UpdateInfo(
            version=str(payload["version"]),
            download_url=str(payload["download_url"]),
            sha256=str(payload["sha256"]).lower(),
            notes=str(payload.get("notes") or ""),
        )
    except (KeyError, TypeError) as error:
        raise UpdateError("Plik aktualizacji nie zawiera wszystkich wymaganych danych.") from error
    if urlparse(info.download_url).scheme != "https" or len(info.sha256) != 64:
        raise UpdateError("Źródło aktualizacji ma nieprawidłowy adres lub sumę SHA-256.")
    return info if version_tuple(info.version) > version_tuple(current_version) else None


def _safe_extract(archive: Path, destination: Path) -> Path:
    with zipfile.ZipFile(archive) as zipped:
        root = destination.resolve()
        for member in zipped.infolist():
            target = (destination / member.filename).resolve()
            if root not in target.parents and target != root:
                raise UpdateError("Archiwum aktualizacji zawiera niedozwoloną ścieżkę.")
        zipped.extractall(destination)
    candidates = [destination]
    candidates.extend(path for path in destination.iterdir() if path.is_dir())
    source = next((path for path in candidates if (path / "app.py").exists()), None)
    if source is None:
        raise UpdateError("Archiwum aktualizacji nie zawiera aplikacji.")
    return source


def prepare_update(info: UpdateInfo, app_directory: Path) -> Path:
    work = Path(tempfile.mkdtemp(prefix="lol-xp-update-"))
    archive = work / "update.zip"
    request = Request(info.download_url, headers={"User-Agent": "LoL-XP-Tracker-Updater"})
    try:
        with urlopen(request, timeout=45) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        shutil.rmtree(work, ignore_errors=True)
        raise UpdateError("Nie udało się pobrać aktualizacji.") from error
    digest = hashlib.sha256(archive.read_bytes()).hexdigest().lower()
    if digest != info.sha256:
        shutil.rmtree(work, ignore_errors=True)
        raise UpdateError("Aktualizacja nie przeszła kontroli bezpieczeństwa SHA-256.")
    payload = work / "payload"
    payload.mkdir()
    source = _safe_extract(archive, payload)

    script = work / "install-update.bat"
    restart = app_directory / "start.bat"
    script.write_text(
        "@echo off\n"
        "timeout /t 3 /nobreak >nul\n"
        f'xcopy /E /I /Y "{source}\\*" "{app_directory}\\" >nul\n'
        f'start "" "{restart}"\n'
        f'rmdir /S /Q "{work}"\n',
        encoding="utf-8",
    )
    return script


def launch_prepared_update(script: Path) -> None:
    if sys.platform != "win32":
        raise UpdateError("Automatyczna instalacja jest dostępna w systemie Windows.")
    subprocess.Popen(
        ["cmd", "/c", str(script)],
        cwd=str(script.parent),
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )
