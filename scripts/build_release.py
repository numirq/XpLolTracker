from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "numirq/XpLolTracker"
INCLUDED_FILES = (
    "app.py",
    "start.bat",
    "build_exe.bat",
    "requirements.txt",
    "README.md",
)


def package_files() -> list[Path]:
    files = [PROJECT_ROOT / name for name in INCLUDED_FILES]
    files.extend(
        path
        for path in (PROJECT_ROOT / "lol_tracker").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    return sorted(files, key=lambda path: path.relative_to(PROJECT_ROOT).as_posix())


def build_archive(destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in package_files():
            relative = source.relative_to(PROJECT_ROOT).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2024, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes(), compresslevel=9)
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a deterministic LoL XP Tracker update archive.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--notes", default="Nowa wersja LoL XP Tracker.")
    arguments = parser.parse_args()

    package_version = arguments.version.strip().lstrip("v")
    expected_version = {}
    exec((PROJECT_ROOT / "lol_tracker" / "__init__.py").read_text(encoding="utf-8"), expected_version)
    if expected_version.get("__version__") != package_version:
        raise SystemExit(
            f"Version mismatch: requested {package_version}, code contains "
            f"{expected_version.get('__version__')}."
        )

    digest = build_archive(arguments.output)
    if arguments.manifest:
        tag = f"v{package_version}"
        manifest = {
            "version": package_version,
            "download_url": (
                f"https://github.com/{REPOSITORY}/releases/download/{tag}/"
                f"{arguments.output.name}"
            ),
            "sha256": digest,
            "notes": arguments.notes,
        }
        arguments.manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(digest)


if __name__ == "__main__":
    main()
