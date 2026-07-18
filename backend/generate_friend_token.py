from __future__ import annotations

import argparse
import hashlib
import json
import secrets


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a private LoL XP Tracker friend token.")
    parser.add_argument(
        "--account",
        action="append",
        required=True,
        help="Allowed Riot ID in GameName#TagLine format. May be repeated.",
    )
    arguments = parser.parse_args()
    for account in arguments.account:
        if "#" not in account or account.startswith("#") or account.endswith("#"):
            raise SystemExit(f"Invalid Riot ID: {account!r}")

    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    print("KOD DLA ZNAJOMEGO (wyświetlany tylko teraz):")
    print(token)
    print("\nFRAGMENT DO SEKRETU ACCESS_RULES:")
    print(json.dumps({digest: arguments.account}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
