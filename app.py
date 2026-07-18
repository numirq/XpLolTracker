from __future__ import annotations

import os
import sys
from pathlib import Path

from lol_tracker.database import Database
from lol_tracker.ui import TrackerApp


def data_directory() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return root / "LoLXPTracker"
    return Path.home() / ".local" / "share" / "lol-xp-tracker"


def main() -> None:
    database = Database(data_directory() / "tracker.db")
    app = TrackerApp(database)
    app.mainloop()


if __name__ == "__main__":
    main()
