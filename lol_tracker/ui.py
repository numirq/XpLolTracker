from __future__ import annotations

import calendar
import secrets
import sqlite3
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable

try:
    import pystray
    from PIL import Image, ImageDraw
except Exception:  # Optional tray backends may also fail on systems without a display.
    pystray = None
    Image = None
    ImageDraw = None

from . import __version__
from .database import Database
from .lcu_client import LcuClient, LcuError
from .riot_api import REGIONAL_ROUTES, RiotApiClient, RiotApiError, parse_backend_invitation
from .updater import (
    DEFAULT_MANIFEST_URL,
    UpdateError,
    check_for_update,
    launch_prepared_update,
    prepare_update,
)
from .xp import calculate_xp_gain, games_to_level_30, progress_percent, xp_to_level_30


COLORS = {
    "bg": "#070b14",
    "sidebar": "#0b1220",
    "card": "#111a2b",
    "card_alt": "#162238",
    "line": "#26344d",
    "text": "#f2f5fa",
    "muted": "#8fa0b8",
    "gold": "#c89b3c",
    "gold_hover": "#e0b65b",
    "teal": "#0ac8b9",
    "green": "#35c978",
    "red": "#ef5b67",
    "input": "#0c1424",
}


PLATFORMS = list(REGIONAL_ROUTES)


def format_date(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone().strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError):
        return value


def format_duration(seconds: int) -> str:
    if not seconds:
        return "—"
    return f"{seconds // 60}:{seconds % 60:02d}"


def parse_int(value: str, label: str, allow_blank: bool = False) -> int | None:
    value = value.strip()
    if allow_blank and not value:
        return None
    try:
        number = int(value)
    except ValueError as error:
        raise ValueError(f"Pole „{label}” musi być liczbą całkowitą.") from error
    if number < 0:
        raise ValueError(f"Pole „{label}” nie może być ujemne.")
    return number


class StyledButton(tk.Button):
    def __init__(self, master: tk.Misc, *, secondary: bool = False, danger: bool = False, **kwargs: Any):
        if danger:
            background, active = COLORS["red"], "#ff7782"
            foreground = "white"
        elif secondary:
            background, active = COLORS["card_alt"], "#223351"
            foreground = COLORS["text"]
        else:
            background, active = COLORS["gold"], COLORS["gold_hover"]
            foreground = "#101722"
        super().__init__(
            master,
            bg=background,
            fg=foreground,
            activebackground=active,
            activeforeground=foreground,
            relief="flat",
            bd=0,
            padx=14,
            pady=9,
            cursor="hand2",
            font=("Segoe UI Semibold", 10),
            **kwargs,
        )


class Card(tk.Frame):
    def __init__(self, master: tk.Misc, **kwargs: Any):
        super().__init__(master, bg=COLORS["card"], highlightthickness=1, highlightbackground=COLORS["line"], **kwargs)


class AccountDialog(tk.Toplevel):
    def __init__(
        self,
        parent: "TrackerApp",
        account: sqlite3.Row | None = None,
        initial: dict[str, Any] | None = None,
    ):
        super().__init__(parent)
        self.parent = parent
        self.account = account
        self.result = False
        initial = initial or {}

        self.title("Edytuj konto" if account else "Dodaj konto")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        values = {
            "game_name": account["game_name"] if account else initial.get("game_name", ""),
            "tag_line": account["tag_line"] if account else initial.get("tag_line", ""),
            "platform": account["platform"] if account else initial.get("platform", "EUW1"),
            "level": account["current_level"] if account else initial.get("level", 1),
            "xp": account["current_xp"] if account else initial.get("xp", 0),
            "required": account["xp_required"] if account else initial.get("xp_required", 0),
        }
        self.vars = {key: tk.StringVar(value=str(value)) for key, value in values.items()}

        box = Card(self)
        box.pack(padx=22, pady=22, fill="both", expand=True)
        tk.Label(
            box,
            text="Dane konta",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI Semibold", 16),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 12))

        self._entry(box, 1, "Riot ID – nazwa", "game_name")
        self._entry(box, 2, "Tag bez #", "tag_line")
        self._combo(box, 3, "Serwer", "platform", PLATFORMS)
        self._entry(box, 4, "Poziom", "level")
        self._entry(box, 5, "Aktualne XP", "xp")
        self._entry(box, 6, "XP wymagane do poziomu (opcjonalne)", "required")

        actions = tk.Frame(box, bg=COLORS["card"])
        actions.grid(row=7, column=0, columnspan=2, sticky="e", padx=18, pady=18)
        StyledButton(actions, text="Anuluj", secondary=True, command=self.destroy).pack(side="left", padx=(0, 8))
        StyledButton(actions, text="Zapisz konto", command=self.save).pack(side="left")

        self.bind("<Return>", lambda _event: self.save())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.update_idletasks()
        self._center(parent)

    def _label(self, parent: tk.Misc, row: int, text: str) -> None:
        tk.Label(parent, text=text, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(
            row=row, column=0, sticky="w", padx=(18, 12), pady=6
        )

    def _entry(self, parent: tk.Misc, row: int, label: str, key: str) -> None:
        self._label(parent, row, label)
        tk.Entry(
            parent,
            textvariable=self.vars[key],
            bg=COLORS["input"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            width=30,
            font=("Segoe UI", 10),
        ).grid(row=row, column=1, sticky="ew", padx=(0, 18), pady=6, ipady=7)

    def _combo(self, parent: tk.Misc, row: int, label: str, key: str, values: list[str]) -> None:
        self._label(parent, row, label)
        combo = ttk.Combobox(parent, textvariable=self.vars[key], values=values, state="readonly", width=28)
        combo.grid(row=row, column=1, sticky="ew", padx=(0, 18), pady=6, ipady=4)

    @staticmethod
    def _center(parent: tk.Misc, window: tk.Toplevel | None = None) -> None:
        target = window or parent.winfo_toplevel()
        target.update_idletasks()

    def save(self) -> None:
        try:
            game_name = self.vars["game_name"].get().strip()
            tag_line = self.vars["tag_line"].get().strip().lstrip("#")
            if not game_name or not tag_line:
                raise ValueError("Wpisz nazwę konta i tag.")
            level = parse_int(self.vars["level"].get(), "Poziom")
            xp = parse_int(self.vars["xp"].get(), "Aktualne XP")
            required = parse_int(self.vars["required"].get() or "0", "XP wymagane")
            if level is None or level < 1:
                raise ValueError("Poziom musi być większy od zera.")
            if required and xp is not None and xp > required:
                raise ValueError("Aktualne XP nie może być większe od wymaganego XP.")

            if self.account:
                self.parent.db.update_account_identity(
                    int(self.account["id"]), game_name, tag_line, self.vars["platform"].get()
                )
                self.parent.db.update_account_progress(
                    int(self.account["id"]), int(level), int(xp or 0), int(required or 0)
                )
                self.parent.selected_account_id = int(self.account["id"])
            else:
                self.parent.selected_account_id = self.parent.db.add_account(
                    game_name,
                    tag_line,
                    self.vars["platform"].get(),
                    int(level),
                    int(xp or 0),
                    int(required or 0),
                )
            self.result = True
            self.destroy()
            self.parent.refresh_all()
        except (ValueError, sqlite3.IntegrityError) as error:
            text = "Takie konto jest już dodane." if isinstance(error, sqlite3.IntegrityError) else str(error)
            messagebox.showerror("Nie można zapisać", text, parent=self)


class GameDialog(tk.Toplevel):
    def __init__(
        self,
        parent: "TrackerApp",
        account: sqlite3.Row,
        initial: dict[str, Any] | sqlite3.Row | None = None,
        game_id: int | None = None,
    ):
        super().__init__(parent)
        self.parent = parent
        self.account = account
        self.game_id = game_id
        source = dict(initial) if initial is not None else {}

        self.title("Edytuj grę" if game_id else "Dodaj grę")
        self.configure(bg=COLORS["bg"])
        available_height = max(560, min(690, self.winfo_screenheight() - 90))
        self.geometry(f"720x{available_height}")
        self.minsize(680, 540)
        self.transient(parent)
        self.grab_set()

        played = source.get("played_at", datetime.now().astimezone().isoformat(timespec="seconds"))
        values = {
            "played_at": format_date(played),
            "champion": source.get("champion", ""),
            "queue_name": source.get("queue_name", "Normal Draft"),
            "role": source.get("role", ""),
            "win": "Wygrana" if source.get("win") in (True, 1) else "Przegrana" if source.get("win") in (False, 0) else "Brak danych",
            "kills": source.get("kills", 0),
            "deaths": source.get("deaths", 0),
            "assists": source.get("assists", 0),
            "cs": source.get("cs", 0),
            "damage": source.get("damage", 0),
            "gold": source.get("gold", 0),
            "vision_score": source.get("vision_score", 0),
            "champion_level": source.get("champion_level", 0),
            "duration": source.get("duration_seconds", 0) // 60 if source.get("duration_seconds") else "",
            "xp_gained": "" if source.get("xp_gained") is None else source.get("xp_gained"),
            "level_after": source.get("level_after", account["current_level"]),
            "xp_after": source.get("xp_after", account["current_xp"]),
            "xp_required_after": source.get("xp_required_after", account["xp_required"]),
            "notes": source.get("notes", ""),
        }
        self.match_id = source.get("match_id")
        self.source_name = source.get("source", "manual")
        self.vars = {key: tk.StringVar(value=str(value)) for key, value in values.items()}

        header = tk.Frame(self, bg=COLORS["bg"])
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(
            header,
            text="Mecz i postęp XP",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Segoe UI Semibold", 20),
        ).pack(anchor="w")
        tk.Label(
            header,
            text=f"{account['game_name']}#{account['tag_line']}  •  {account['platform']}",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(3, 0))

        actions = tk.Frame(self, bg=COLORS["bg"])
        actions.pack(side="bottom", fill="x", padx=24, pady=(8, 18))
        StyledButton(actions, text="Anuluj", secondary=True, command=self.destroy).pack(side="right", padx=(8, 0))
        StyledButton(actions, text="Zapisz grę", command=self.save).pack(side="right")

        body_shell = Card(self)
        body_shell.pack(fill="both", expand=True, padx=24, pady=(0, 4))
        canvas = tk.Canvas(body_shell, bg=COLORS["card"], highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(body_shell, orient="vertical", command=canvas.yview)
        body = tk.Frame(canvas, bg=COLORS["card"])
        body_window = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        body.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(body_window, width=event.width),
        )
        self.bind(
            "<MouseWheel>",
            lambda event: canvas.yview_scroll(int(-event.delta / 120), "units"),
        )
        body.columnconfigure(1, weight=1)
        body.columnconfigure(3, weight=1)

        fields = [
            ("Data i godzina", "played_at", 0, 0),
            ("Bohater", "champion", 0, 2),
            ("Tryb", "queue_name", 1, 0),
            ("Pozycja", "role", 1, 2),
            ("Wynik", "win", 2, 0),
            ("Czas gry (min)", "duration", 2, 2),
            ("Zabójstwa", "kills", 3, 0),
            ("Śmierci", "deaths", 3, 2),
            ("Asysty", "assists", 4, 0),
            ("CS", "cs", 4, 2),
            ("Obrażenia bohaterom", "damage", 5, 0),
            ("Zdobyte XP", "xp_gained", 5, 2),
            ("Poziom po grze", "level_after", 6, 0),
            ("XP po grze", "xp_after", 6, 2),
            ("XP wymagane do poziomu", "xp_required_after", 7, 0),
            ("Poziom bohatera", "champion_level", 7, 2),
            ("Zdobyte złoto", "gold", 8, 0),
            ("Vision score", "vision_score", 8, 2),
        ]
        for label, key, row, column in fields:
            self._field(body, label, key, row, column)

        tk.Label(body, text="Notatka", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(
            row=9, column=0, sticky="w", padx=(18, 8), pady=(9, 5)
        )
        notes = tk.Entry(
            body,
            textvariable=self.vars["notes"],
            bg=COLORS["input"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=("Segoe UI", 10),
        )
        notes.grid(row=9, column=1, columnspan=3, sticky="ew", padx=(0, 18), pady=(9, 5), ipady=7)

        tk.Label(
            body,
            text="Jeśli zostawisz „Zdobyte XP” puste, aplikacja spróbuje obliczyć je ze stanu przed i po grze.",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9),
            wraplength=630,
            justify="left",
        ).grid(row=10, column=0, columnspan=4, sticky="w", padx=18, pady=(12, 18))

        self.bind("<Control-Return>", lambda _event: self.save())
        self.bind("<Escape>", lambda _event: self.destroy())

    def _field(self, parent: tk.Misc, label: str, key: str, row: int, column: int) -> None:
        frame = tk.Frame(parent, bg=COLORS["card"])
        frame.grid(row=row, column=column, columnspan=2, sticky="ew", padx=(18 if column == 0 else 8, 18), pady=7)
        frame.columnconfigure(0, weight=1)
        tk.Label(frame, text=label, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        if key == "win":
            widget: tk.Widget = ttk.Combobox(
                frame, textvariable=self.vars[key], values=["Wygrana", "Przegrana", "Brak danych"], state="readonly"
            )
        else:
            widget = tk.Entry(
                frame,
                textvariable=self.vars[key],
                bg=COLORS["input"],
                fg=COLORS["text"],
                insertbackground=COLORS["text"],
                relief="flat",
                font=("Segoe UI", 10),
            )
        widget.grid(row=1, column=0, sticky="ew", ipady=6)

    def save(self) -> None:
        try:
            champion = self.vars["champion"].get().strip()
            if not champion:
                raise ValueError("Wpisz nazwę bohatera.")
            try:
                played = datetime.strptime(self.vars["played_at"].get().strip(), "%d.%m.%Y %H:%M")
                played_at = played.astimezone().isoformat(timespec="seconds")
            except ValueError as error:
                raise ValueError("Data musi mieć format DD.MM.RRRR GG:MM.") from error

            numeric = {}
            for key, label in [
                ("kills", "Zabójstwa"), ("deaths", "Śmierci"), ("assists", "Asysty"),
                ("cs", "CS"), ("damage", "Obrażenia"), ("duration", "Czas gry"),
                ("gold", "Zdobyte złoto"), ("vision_score", "Vision score"),
                ("champion_level", "Poziom bohatera"),
                ("level_after", "Poziom po grze"), ("xp_after", "XP po grze"),
                ("xp_required_after", "XP wymagane"),
            ]:
                numeric[key] = int(parse_int(self.vars[key].get() or "0", label) or 0)
            xp_gain = parse_int(self.vars["xp_gained"].get(), "Zdobyte XP", allow_blank=True)
            if xp_gain is None:
                xp_gain = calculate_xp_gain(
                    int(self.account["current_level"]),
                    int(self.account["current_xp"]),
                    int(self.account["xp_required"]),
                    numeric["level_after"],
                    numeric["xp_after"],
                )
            required = numeric["xp_required_after"]
            if required and numeric["xp_after"] > required:
                raise ValueError("XP po grze nie może być większe od wymaganego XP.")
            if numeric["level_after"] < 1:
                raise ValueError("Poziom po grze musi być większy od zera.")

            win_value = self.vars["win"].get()
            data = {
                "match_id": self.match_id,
                "played_at": played_at,
                "champion": champion,
                "queue_name": self.vars["queue_name"].get().strip() or "Nieznany",
                "role": self.vars["role"].get().strip(),
                "win": True if win_value == "Wygrana" else False if win_value == "Przegrana" else None,
                "kills": numeric["kills"],
                "deaths": numeric["deaths"],
                "assists": numeric["assists"],
                "cs": numeric["cs"],
                "damage": numeric["damage"],
                "gold": numeric["gold"],
                "vision_score": numeric["vision_score"],
                "champion_level": numeric["champion_level"],
                "duration_seconds": numeric["duration"] * 60,
                "xp_gained": xp_gain,
                "level_after": numeric["level_after"],
                "xp_after": numeric["xp_after"],
                "xp_required_after": required,
                "source": self.source_name,
                "notes": self.vars["notes"].get().strip(),
            }
            if self.game_id:
                self.parent.db.update_game(self.game_id, int(self.account["id"]), data)
                self.parent.db.recalculate_account(int(self.account["id"]))
            else:
                self.parent.db.add_game(int(self.account["id"]), data)
            self.destroy()
            self.parent.refresh_all()
        except (ValueError, sqlite3.IntegrityError) as error:
            text = "Ten mecz jest już zapisany dla tego konta." if isinstance(error, sqlite3.IntegrityError) else str(error)
            messagebox.showerror("Nie można zapisać gry", text, parent=self)


class ApiSettingsDialog(tk.Toplevel):
    def __init__(self, parent: "TrackerApp"):
        super().__init__(parent)
        self.parent = parent
        self.title("Połączenie z danymi meczów")
        self.configure(bg=COLORS["bg"])
        self.geometry("650x700")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        box = Card(self)
        box.pack(padx=22, pady=22, fill="both", expand=True)
        tk.Label(
            box, text="Prywatny serwer trackera", bg=COLORS["card"], fg=COLORS["text"],
            font=("Segoe UI Semibold", 16)
        ).pack(anchor="w", padx=18, pady=(18, 4))
        tk.Label(
            box,
            text="Wklej zaproszenie od właściciela. Kod jest przypisany do profilu znajomego, działa dla jego kont i nie wygasa samoczynnie.",
            bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9),
            wraplength=570, justify="left"
        ).pack(anchor="w", padx=18, pady=(0, 10))

        tk.Label(
            box, text="Zaproszenie jednym wklejeniem", bg=COLORS["card"], fg=COLORS["muted"],
            font=("Segoe UI Semibold", 8)
        ).pack(anchor="w", padx=18)
        invite_row = tk.Frame(box, bg=COLORS["card"])
        invite_row.pack(fill="x", padx=18, pady=(5, 13))
        self.invitation = tk.StringVar()
        invite_entry = tk.Entry(
            invite_row, textvariable=self.invitation, bg=COLORS["input"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat", font=("Consolas", 9)
        )
        invite_entry.pack(side="left", fill="x", expand=True, ipady=8)
        StyledButton(
            invite_row, text="Wczytaj", secondary=True, command=self.import_invitation
        ).pack(side="left", padx=(8, 0))

        tk.Label(
            box, text="Adres serwera HTTPS", bg=COLORS["card"], fg=COLORS["muted"],
            font=("Segoe UI Semibold", 8)
        ).pack(anchor="w", padx=18)
        self.backend_url = tk.StringVar(value=parent.db.get_setting("backend_url"))
        backend_entry = tk.Entry(
            box, textvariable=self.backend_url, bg=COLORS["input"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat", font=("Consolas", 9)
        )
        backend_entry.pack(fill="x", padx=18, pady=(5, 12), ipady=8)

        tk.Label(
            box, text="Twój kod dostępu", bg=COLORS["card"], fg=COLORS["muted"],
            font=("Segoe UI Semibold", 8)
        ).pack(anchor="w", padx=18)
        self.access_token = tk.StringVar(value=parent.db.get_setting("backend_access_token"))
        token_entry = tk.Entry(
            box, textvariable=self.access_token, show="•", bg=COLORS["input"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat", font=("Consolas", 9)
        )
        token_entry.pack(fill="x", padx=18, pady=(5, 16), ipady=8)

        separator = tk.Frame(box, bg=COLORS["line"], height=1)
        separator.pack(fill="x", padx=18, pady=(2, 14))
        tk.Label(
            box, text="TRYB DEWELOPERSKI — OPCJONALNIE", bg=COLORS["card"], fg=COLORS["muted"],
            font=("Segoe UI Semibold", 8)
        ).pack(anchor="w", padx=18)
        tk.Label(
            box,
            text="Lokalny klucz Development jest używany tylko wtedy, gdy prywatny serwer nie został skonfigurowany.",
            bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9),
            wraplength=570, justify="left"
        ).pack(anchor="w", padx=18, pady=(4, 7))
        self.local_key = tk.StringVar(value=parent.db.get_setting("riot_api_key"))
        local_key_entry = tk.Entry(
            box, textvariable=self.local_key, show="•", bg=COLORS["input"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat", font=("Consolas", 9)
        )
        local_key_entry.pack(fill="x", padx=18, pady=(0, 8), ipady=8)
        (invite_entry if not self.backend_url.get() else token_entry).focus_set()
        invite_entry.bind("<Return>", lambda _event: self.import_invitation())

        actions = tk.Frame(box, bg=COLORS["card"])
        actions.pack(side="bottom", fill="x", padx=18, pady=18)
        StyledButton(actions, text="Zapisz", command=self.save).pack(side="right")
        StyledButton(actions, text="Anuluj", secondary=True, command=self.destroy).pack(side="right", padx=(0, 8))

    def import_invitation(self) -> None:
        try:
            invitation = parse_backend_invitation(self.invitation.get())
        except RiotApiError as error:
            messagebox.showerror("Nieprawidłowe zaproszenie", str(error), parent=self)
            return
        self.backend_url.set(invitation["server"])
        self.access_token.set(invitation["token"])
        self.invitation.set("")
        messagebox.showinfo(
            "Zaproszenie wczytane",
            "Adres serwera i bezterminowy kod dostępu są gotowe. Kliknij „Zapisz”.",
            parent=self,
        )

    def save(self) -> None:
        backend_url = self.backend_url.get().strip().rstrip("/")
        access_token = self.access_token.get().strip()
        if bool(backend_url) != bool(access_token):
            messagebox.showerror(
                "Niepełne ustawienia",
                "Wpisz jednocześnie adres prywatnego serwera i kod dostępu.",
                parent=self,
            )
            return
        if backend_url and not backend_url.startswith("https://"):
            messagebox.showerror(
                "Nieprawidłowy adres",
                "Adres prywatnego serwera musi rozpoczynać się od https://",
                parent=self,
            )
            return
        self.parent.db.set_setting("backend_url", backend_url)
        self.parent.db.set_setting("backend_access_token", access_token)
        self.parent.db.set_setting("riot_api_key", self.local_key.get().strip())
        configured = bool((backend_url and access_token) or self.local_key.get().strip())
        self.parent.db.set_setting("riot_api_state", "unknown" if configured else "missing")
        self.destroy()
        self.parent.refresh_api_state()
        self.parent.set_status("Zapisano ustawienia połączenia.", COLORS["green"])


class MatchDetailsDialog(tk.Toplevel):
    def __init__(self, parent: "TrackerApp", account: sqlite3.Row, game: sqlite3.Row):
        super().__init__(parent)
        self.parent = parent
        self.account = account
        self.game = game
        self.title(f"Szczegóły meczu – {game['champion']}")
        self.configure(bg=COLORS["bg"])
        self.geometry(f"700x{max(560, min(650, self.winfo_screenheight() - 100))}")
        self.minsize(650, 520)
        self.transient(parent)

        won = game["win"] == 1
        result = "Wygrana" if won else "Przegrana" if game["win"] == 0 else "Brak wyniku"
        result_color = COLORS["green"] if won else COLORS["red"] if game["win"] == 0 else COLORS["muted"]

        header = tk.Frame(self, bg=COLORS["bg"])
        header.pack(fill="x", padx=24, pady=(20, 12))
        tk.Label(
            header, text=game["champion"], bg=COLORS["bg"], fg=COLORS["text"],
            font=("Segoe UI Semibold", 22),
        ).pack(side="left")
        tk.Label(
            header, text=result, bg=COLORS["bg"], fg=result_color,
            font=("Segoe UI Semibold", 15),
        ).pack(side="right")

        subtitle = (
            f"{format_date(game['played_at'])}  •  {game['queue_name']}"
            + (f"  •  {game['role']}" if game["role"] else "")
        )
        tk.Label(
            self, text=subtitle, bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 10),
        ).pack(anchor="w", padx=24, pady=(0, 10))

        content = Card(self)
        content.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        details = [
            ("K / D / A", f"{game['kills']} / {game['deaths']} / {game['assists']}"),
            ("CS", str(game["cs"])),
            ("Obrażenia bohaterom", f"{game['damage']:,}".replace(",", " ")),
            ("Zdobyte złoto", f"{game['gold']:,}".replace(",", " ") if game["gold"] else "—"),
            ("Vision score", str(game["vision_score"]) if game["vision_score"] else "—"),
            ("Poziom bohatera", str(game["champion_level"]) if game["champion_level"] else "—"),
            ("Czas gry", format_duration(game["duration_seconds"])),
            ("Zdobyte XP", f"+{game['xp_gained']}" if game["xp_gained"] is not None else "—"),
            ("Stan konta po grze", f"Poziom {game['level_after']} • {game['xp_after']} XP"),
            ("Źródło wpisu", game["source"]),
        ]
        for index, (label, value) in enumerate(details):
            cell = tk.Frame(content, bg=COLORS["card_alt"])
            cell.grid(row=index // 2, column=index % 2, sticky="nsew", padx=8, pady=7)
            tk.Label(
                cell, text=label.upper(), bg=COLORS["card_alt"], fg=COLORS["muted"],
                font=("Segoe UI Semibold", 8),
            ).pack(anchor="w", padx=13, pady=(10, 2))
            tk.Label(
                cell, text=value, bg=COLORS["card_alt"], fg=COLORS["text"],
                font=("Segoe UI Semibold", 12),
            ).pack(anchor="w", padx=13, pady=(0, 10))

        if game["notes"]:
            tk.Label(
                content, text=f"Notatka: {game['notes']}", bg=COLORS["card"], fg=COLORS["muted"],
                font=("Segoe UI", 9), wraplength=610, justify="left",
            ).grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 12))

        actions = tk.Frame(self, bg=COLORS["bg"])
        actions.pack(fill="x", padx=24, pady=(0, 18))
        StyledButton(actions, text="Zamknij", secondary=True, command=self.destroy).pack(side="right", padx=(8, 0))
        StyledButton(actions, text="Edytuj wpis", command=self._edit).pack(side="right")
        missing_details = not game["gold"] or not game["champion_level"]
        if game["match_id"] and missing_details:
            StyledButton(
                actions, text="Uzupełnij dane z Riot", secondary=True, command=self._refresh_details
            ).pack(side="left")
        self.bind("<Escape>", lambda _event: self.destroy())

    def _edit(self) -> None:
        game_id = int(self.game["id"])
        self.destroy()
        self.parent.edit_game_by_id(game_id)

    def _refresh_details(self) -> None:
        game_id = int(self.game["id"])
        self.destroy()
        self.parent.refresh_game_details(game_id)


class UpdateSettingsDialog(tk.Toplevel):
    def __init__(self, parent: "TrackerApp"):
        super().__init__(parent)
        self.parent = parent
        self.title("Aktualizacje")
        self.configure(bg=COLORS["bg"])
        self.geometry("620x390")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        box = Card(self)
        box.pack(fill="both", expand=True, padx=22, pady=22)
        tk.Label(
            box, text="Automatyczne aktualizacje", bg=COLORS["card"], fg=COLORS["text"],
            font=("Segoe UI Semibold", 17),
        ).pack(anchor="w", padx=18, pady=(18, 3))
        tk.Label(
            box, text=f"Zainstalowana wersja: {__version__}", bg=COLORS["card"], fg=COLORS["teal"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=18, pady=(0, 14))
        tk.Label(
            box,
            text="Adres pliku manifestu aktualizacji (HTTPS). Po podłączeniu repozytorium aplikacja będzie sprawdzać go przy każdym uruchomieniu.",
            bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9),
            wraplength=540, justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 7))
        self.url = tk.StringVar(
            value=parent.db.get_setting("update_manifest_url", DEFAULT_MANIFEST_URL)
        )
        tk.Entry(
            box, textvariable=self.url, bg=COLORS["input"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat", font=("Segoe UI", 9),
        ).pack(fill="x", padx=18, pady=(0, 10), ipady=7)
        self.auto = tk.BooleanVar(value=parent.db.get_setting("auto_updates", "1") == "1")
        tk.Checkbutton(
            box, text="Sprawdzaj automatycznie przy uruchomieniu", variable=self.auto,
            bg=COLORS["card"], fg=COLORS["text"], activebackground=COLORS["card"],
            activeforeground=COLORS["text"], selectcolor=COLORS["input"], font=("Segoe UI", 9),
        ).pack(anchor="w", padx=14, pady=(0, 10))
        actions = tk.Frame(box, bg=COLORS["card"])
        actions.pack(fill="x", padx=18, pady=(6, 18))
        StyledButton(actions, text="Zapisz", command=self.save).pack(side="right")
        StyledButton(actions, text="Sprawdź teraz", secondary=True, command=self.check_now).pack(side="right", padx=(0, 8))
        StyledButton(actions, text="Anuluj", secondary=True, command=self.destroy).pack(side="left")

    def _save_values(self) -> None:
        self.parent.db.set_setting("update_manifest_url", self.url.get().strip())
        self.parent.db.set_setting("auto_updates", "1" if self.auto.get() else "0")

    def save(self) -> None:
        self._save_values()
        self.destroy()
        self.parent.set_status("Zapisano ustawienia aktualizacji.", COLORS["green"])

    def check_now(self) -> None:
        self._save_values()
        self.destroy()
        self.parent.check_updates(silent=False)


class AboutDialog(tk.Toplevel):
    def __init__(self, parent: "TrackerApp"):
        super().__init__(parent)
        self.title("O aplikacji")
        self.configure(bg=COLORS["bg"])
        self.geometry("650x570")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        box = Card(self)
        box.pack(fill="both", expand=True, padx=22, pady=22)
        tk.Label(
            box, text="LoL XP Tracker", bg=COLORS["card"], fg=COLORS["gold"],
            font=("Segoe UI Semibold", 21),
        ).pack(anchor="w", padx=20, pady=(20, 2))
        tk.Label(
            box, text=f"Wersja {__version__}", bg=COLORS["card"], fg=COLORS["teal"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=20, pady=(0, 16))

        sections = [
            (
                "PRYWATNOŚĆ",
                "Historia gier, ustawienia oraz profile są przechowywane lokalnie na komputerze użytkownika. Prywatny backend otrzymuje wyłącznie Riot ID potrzebne do pobrania wskazanego meczu i nie otrzymuje lokalnej bazy danych.",
            ),
            (
                "DZIAŁANIE",
                "Aplikacja odczytuje postęp XP z lokalnego klienta League of Legends oraz pobiera historię meczów z oficjalnego Riot Games API. Nie steruje grą i nie zapewnia przewagi podczas rozgrywki.",
            ),
            (
                "INFORMACJA PRAWNA",
                "LoL XP Tracker jest niezależnym narzędziem społecznościowym i nie jest zatwierdzony ani sponsorowany przez Riot Games. Nie reprezentuje opinii Riot Games ani osób zaangażowanych w tworzenie lub zarządzanie produktami Riot. Riot Games oraz powiązane właściwości są znakami towarowymi lub zarejestrowanymi znakami towarowymi Riot Games, Inc.",
            ),
            (
                "LEGAL NOTICE",
                "LoL XP Tracker isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.",
            ),
        ]
        for title, text in sections:
            tk.Label(
                box, text=title, bg=COLORS["card"], fg=COLORS["muted"],
                font=("Segoe UI Semibold", 8),
            ).pack(anchor="w", padx=20, pady=(7, 3))
            tk.Label(
                box, text=text, bg=COLORS["card"], fg=COLORS["text"],
                font=("Segoe UI", 9), wraplength=575, justify="left",
            ).pack(anchor="w", padx=20)

        StyledButton(box, text="Zamknij", command=self.destroy).pack(side="bottom", anchor="e", padx=20, pady=20)
        self.bind("<Escape>", lambda _event: self.destroy())


class SessionDialog(tk.Toplevel):
    def __init__(self, parent: "TrackerApp", account: sqlite3.Row):
        super().__init__(parent)
        self.parent = parent
        self.account = account
        width = max(760, min(960, self.winfo_screenwidth() - 80))
        height = max(540, min(680, self.winfo_screenheight() - 100))
        self.title("Podsumowanie i bohaterowie")
        self.geometry(f"{width}x{height}")
        self.minsize(740, 520)
        self.configure(bg=COLORS["bg"])
        self.transient(parent)

        today = parent.db.stats_today(int(account["id"]))
        session = parent.db.stats_created_since(int(account["id"]), parent.session_started_at)
        overall = parent.db.stats(int(account["id"]))
        average = float(overall["avg_xp"] or 0)
        remaining = xp_to_level_30(
            int(account["current_level"]), int(account["current_xp"]), int(account["xp_required"])
        )
        estimated_games = games_to_level_30(
            int(account["current_level"]), int(account["current_xp"]),
            int(account["xp_required"]), average,
        )

        header = tk.Frame(self, bg=COLORS["bg"])
        header.pack(fill="x", padx=24, pady=(20, 12))
        tk.Label(
            header, text="Podsumowanie grind’u", bg=COLORS["bg"], fg=COLORS["text"],
            font=("Segoe UI Semibold", 21),
        ).pack(anchor="w")
        tk.Label(
            header,
            text=f"{account['game_name']}#{account['tag_line']}  •  poziom {account['current_level']}",
            bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(2, 0))

        road = Card(self)
        road.pack(fill="x", padx=24, pady=(0, 12))
        tk.Label(
            road, text="DROGA DO 30 POZIOMU", bg=COLORS["card"], fg=COLORS["muted"],
            font=("Segoe UI Semibold", 8),
        ).pack(anchor="w", padx=18, pady=(14, 3))
        estimate_text = f"około {estimated_games} gier" if estimated_games is not None else "zagraj więcej gier, aby obliczyć"
        tk.Label(
            road,
            text=f"Pozostało {remaining:,} XP  •  {estimate_text}".replace(",", " "),
            bg=COLORS["card"], fg=COLORS["gold"], font=("Segoe UI Semibold", 15),
        ).pack(anchor="w", padx=18, pady=(0, 14))

        cards = tk.Frame(self, bg=COLORS["bg"])
        cards.pack(fill="x", padx=18, pady=(0, 12))
        decided = int(today["decided"] or 0)
        wins = int(today["wins"] or 0)
        duration_minutes = int(today["duration_seconds"] or 0) // 60
        card_data = [
            ("GRY DZISIAJ", str(today["games"])),
            ("XP DZISIAJ", f"+{int(today['total_xp'] or 0)}"),
            ("ŚREDNIE XP", f"{float(today['avg_xp'] or 0):.0f}" if today["avg_xp"] else "—"),
            ("WIN RATE", f"{wins / decided * 100:.0f}%" if decided else "—"),
            ("CZAS W GRZE", f"{duration_minutes // 60}h {duration_minutes % 60:02d}m"),
        ]
        for index, (title, value) in enumerate(card_data):
            card = Card(cards)
            card.grid(row=0, column=index, sticky="nsew", padx=6)
            cards.columnconfigure(index, weight=1)
            tk.Label(
                card, text=value, bg=COLORS["card"], fg=COLORS["text"],
                font=("Segoe UI Semibold", 17),
            ).pack(padx=12, pady=(13, 2))
            tk.Label(
                card, text=title, bg=COLORS["card"], fg=COLORS["muted"],
                font=("Segoe UI Semibold", 8),
            ).pack(padx=12, pady=(0, 12))

        session_text = (
            f"Od uruchomienia trackera: {session['games']} gier  •  "
            f"+{int(session['total_xp'] or 0)} XP  •  "
            f"{int(session['duration_seconds'] or 0) // 60} min w grze"
        )
        tk.Label(
            self, text=session_text, bg=COLORS["bg"], fg=COLORS["teal"], font=("Segoe UI", 9),
        ).pack(anchor="w", padx=25, pady=(0, 8))

        champions = Card(self)
        champions.pack(fill="both", expand=True, padx=24, pady=(0, 18))
        tk.Label(
            champions, text="Statystyki bohaterów", bg=COLORS["card"], fg=COLORS["text"],
            font=("Segoe UI Semibold", 14),
        ).pack(anchor="w", padx=16, pady=(13, 8))
        columns = ("champion", "games", "winrate", "kda", "avg_xp", "total_xp", "time")
        tree = ttk.Treeview(champions, columns=columns, show="headings")
        labels = {
            "champion": "BOHATER", "games": "GRY", "winrate": "WIN RATE", "kda": "ŁĄCZNE K/D/A",
            "avg_xp": "ŚR. XP", "total_xp": "SUMA XP", "time": "CZAS",
        }
        widths = {"champion": 140, "games": 55, "winrate": 85, "kda": 120, "avg_xp": 75, "total_xp": 80, "time": 80}
        for column in columns:
            tree.heading(column, text=labels[column])
            tree.column(column, width=widths[column], anchor="w", stretch=column == "champion")
        for row in parent.db.champion_stats(int(account["id"])):
            row_decided = int(row["decided"] or 0)
            row_winrate = f"{int(row['wins'] or 0) / row_decided * 100:.0f}%" if row_decided else "—"
            minutes = int(row["duration_seconds"] or 0) // 60
            tree.insert(
                "", "end",
                values=(
                    row["champion"], row["games"], row_winrate,
                    f"{row['kills']} / {row['deaths']} / {row['assists']}",
                    f"{float(row['avg_xp'] or 0):.0f}" if row["avg_xp"] else "—",
                    int(row["total_xp"] or 0), f"{minutes // 60}h {minutes % 60:02d}m",
                ),
            )
        scrollbar = ttk.Scrollbar(champions, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(0, 16))
        scrollbar.pack(side="right", fill="y", padx=(0, 12), pady=(0, 16))

        self.bind("<Escape>", lambda _event: self.destroy())


class Toast(tk.Toplevel):
    def __init__(self, parent: "TrackerApp", title: str, message: str, color: str = COLORS["green"]):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=color)
        shell = tk.Frame(self, bg=COLORS["card"], highlightthickness=1, highlightbackground=color)
        shell.pack(padx=2, pady=2, fill="both", expand=True)
        tk.Label(
            shell, text=title, bg=COLORS["card"], fg=color, font=("Segoe UI Semibold", 11),
        ).pack(anchor="w", padx=16, pady=(12, 3))
        tk.Label(
            shell, text=message, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9),
            justify="left", wraplength=320,
        ).pack(anchor="w", padx=16, pady=(0, 13))
        self.update_idletasks()
        x = self.winfo_screenwidth() - self.winfo_reqwidth() - 24
        y = self.winfo_screenheight() - self.winfo_reqheight() - 64
        self.geometry(f"+{x}+{y}")
        self.after(6500, self.destroy)
        self.bind("<Button-1>", lambda _event: self.destroy())


class ActivityCalendarDialog(tk.Toplevel):
    MONTHS = [
        "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
        "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień",
    ]

    def __init__(self, parent: "TrackerApp", account: sqlite3.Row):
        super().__init__(parent)
        self.parent = parent
        self.account = account
        now = datetime.now()
        self.year, self.month = now.year, now.month
        self.title("Kalendarz aktywności")
        self.configure(bg=COLORS["bg"])
        self.geometry(f"860x{max(600, min(700, self.winfo_screenheight() - 90))}")
        self.minsize(780, 570)
        self.transient(parent)

        header = tk.Frame(self, bg=COLORS["bg"])
        header.pack(fill="x", padx=24, pady=(20, 12))
        tk.Label(
            header, text="Kalendarz aktywności", bg=COLORS["bg"], fg=COLORS["text"],
            font=("Segoe UI Semibold", 21),
        ).pack(anchor="w")
        tk.Label(
            header, text=f"{account['game_name']}#{account['tag_line']}", bg=COLORS["bg"],
            fg=COLORS["muted"], font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(2, 0))

        nav = tk.Frame(self, bg=COLORS["bg"])
        nav.pack(fill="x", padx=24, pady=(0, 10))
        StyledButton(nav, text="‹", secondary=True, command=lambda: self.change_month(-1)).pack(side="left")
        StyledButton(nav, text="›", secondary=True, command=lambda: self.change_month(1)).pack(side="right")
        self.month_label = tk.Label(
            nav, text="", bg=COLORS["bg"], fg=COLORS["gold"], font=("Segoe UI Semibold", 15),
        )
        self.month_label.pack()

        self.calendar_card = Card(self)
        self.calendar_card.pack(fill="both", expand=True, padx=24, pady=(0, 10))
        self.summary_label = tk.Label(
            self, text="", bg=COLORS["bg"], fg=COLORS["teal"], font=("Segoe UI", 10),
        )
        self.summary_label.pack(anchor="w", padx=25, pady=(0, 18))
        self.render_month()
        self.bind("<Left>", lambda _event: self.change_month(-1))
        self.bind("<Right>", lambda _event: self.change_month(1))
        self.bind("<Escape>", lambda _event: self.destroy())

    def change_month(self, direction: int) -> None:
        self.month += direction
        if self.month < 1:
            self.month, self.year = 12, self.year - 1
        elif self.month > 12:
            self.month, self.year = 1, self.year + 1
        self.render_month()

    def render_month(self) -> None:
        for child in self.calendar_card.winfo_children():
            child.destroy()
        self.month_label.configure(text=f"{self.MONTHS[self.month - 1]} {self.year}")
        for column, name in enumerate(["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Niedz"]):
            self.calendar_card.columnconfigure(column, weight=1)
            tk.Label(
                self.calendar_card, text=name, bg=COLORS["card"], fg=COLORS["muted"],
                font=("Segoe UI Semibold", 9),
            ).grid(row=0, column=column, sticky="ew", padx=4, pady=(10, 6))

        activity = self.parent.db.activity_for_month(
            int(self.account["id"]), self.year, self.month
        )
        today = datetime.now().date()
        weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(self.year, self.month)
        for row_index, week in enumerate(weeks, start=1):
            self.calendar_card.rowconfigure(row_index, weight=1)
            for column, day in enumerate(week):
                if day == 0:
                    tk.Frame(self.calendar_card, bg=COLORS["card"]).grid(
                        row=row_index, column=column, sticky="nsew", padx=4, pady=4
                    )
                    continue
                key = f"{self.year:04d}-{self.month:02d}-{day:02d}"
                stats = activity.get(key, {"games": 0, "xp": 0, "wins": 0})
                games = stats["games"]
                cell_color = (
                    COLORS["card_alt"] if games == 0 else
                    "#153b3b" if games == 1 else
                    "#116158" if games == 2 else "#087f72"
                )
                is_today = today.year == self.year and today.month == self.month and today.day == day
                cell = tk.Frame(
                    self.calendar_card, bg=cell_color, highlightthickness=2 if is_today else 1,
                    highlightbackground=COLORS["gold"] if is_today else COLORS["line"],
                )
                cell.grid(row=row_index, column=column, sticky="nsew", padx=4, pady=4)
                tk.Label(
                    cell, text=str(day), bg=cell_color, fg=COLORS["text"],
                    font=("Segoe UI Semibold", 10),
                ).pack(anchor="nw", padx=8, pady=(6, 1))
                if games:
                    tk.Label(
                        cell, text=f"{games} gier\n+{stats['xp']} XP",
                        bg=cell_color, fg="white", font=("Segoe UI", 8), justify="left",
                    ).pack(anchor="sw", padx=8, pady=(1, 6))

        total_games = sum(value["games"] for value in activity.values())
        total_xp = sum(value["xp"] for value in activity.values())
        active_days = sum(1 for value in activity.values() if value["games"])
        self.summary_label.configure(
            text=f"W tym miesiącu: {total_games} gier  •  +{total_xp} XP  •  {active_days} aktywnych dni"
        )


class TrackerApp(tk.Tk):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.session_started_at = datetime.now().astimezone().isoformat(timespec="seconds")
        self.selected_account_id: int | None = None
        self.busy = False
        self.poll_busy = False
        self._closing = False
        self.unknown_account_prompted: set[str] = set()
        self.tray_icon = None

        self.title("LoL XP Tracker")
        self.geometry("1260x780")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self._configure_style()
        self._build_layout()

        accounts = self.db.list_accounts()
        if accounts:
            self.selected_account_id = int(accounts[0]["id"])
        self.refresh_all()
        self.after(5000, self._poll_client)
        manifest_url = self.db.get_setting("update_manifest_url", DEFAULT_MANIFEST_URL)
        if self.db.get_setting("auto_updates", "1") == "1" and manifest_url:
            self.after(9000, lambda: self.check_updates(silent=True))

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Treeview", background=COLORS["card"], foreground=COLORS["text"],
            fieldbackground=COLORS["card"], rowheight=36, borderwidth=0, font=("Segoe UI", 9)
        )
        style.map("Treeview", background=[("selected", "#203655")], foreground=[("selected", "white")])
        style.configure(
            "Treeview.Heading", background=COLORS["card_alt"], foreground=COLORS["muted"],
            relief="flat", font=("Segoe UI Semibold", 9), padding=(8, 8)
        )
        style.map("Treeview.Heading", background=[("active", COLORS["card_alt"])])
        style.configure(
            "XP.Horizontal.TProgressbar", troughcolor=COLORS["input"], background=COLORS["teal"],
            bordercolor=COLORS["input"], lightcolor=COLORS["teal"], darkcolor=COLORS["teal"]
        )
        style.configure(
            "TCombobox", fieldbackground=COLORS["input"], background=COLORS["card_alt"],
            foreground=COLORS["text"], arrowcolor=COLORS["text"],
            bordercolor=COLORS["line"], lightcolor=COLORS["input"], darkcolor=COLORS["input"],
            selectbackground=COLORS["card_alt"], selectforeground=COLORS["text"]
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", COLORS["input"]), ("disabled", COLORS["input"])],
            foreground=[("readonly", COLORS["text"]), ("disabled", COLORS["muted"])],
            background=[("readonly", COLORS["card_alt"]), ("active", COLORS["card_alt"])],
            selectbackground=[("readonly", COLORS["input"])],
            selectforeground=[("readonly", COLORS["text"])],
            arrowcolor=[("readonly", COLORS["text"])],
        )
        self.option_add("*TCombobox*Listbox.background", COLORS["input"])
        self.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
        self.option_add("*TCombobox*Listbox.selectBackground", COLORS["card_alt"])
        self.option_add("*TCombobox*Listbox.selectForeground", COLORS["text"])

    def _build_layout(self) -> None:
        self.sidebar = tk.Frame(self, bg=COLORS["sidebar"], width=250)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        brand.pack(fill="x", padx=20, pady=(24, 18))
        tk.Label(brand, text="LOL", bg=COLORS["sidebar"], fg=COLORS["gold"], font=("Georgia", 18, "bold")).pack(side="left")
        tk.Label(brand, text=" XP TRACKER", bg=COLORS["sidebar"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(side="left")

        tk.Label(
            self.sidebar, text="TWOJE KONTA", bg=COLORS["sidebar"], fg=COLORS["muted"],
            font=("Segoe UI Semibold", 8)
        ).pack(anchor="w", padx=20, pady=(4, 8))

        self.accounts_frame = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        self.accounts_frame.pack(fill="x", padx=10)

        StyledButton(self.sidebar, text="+ Dodaj konto", secondary=True, command=self.add_account).pack(
            fill="x", padx=16, pady=(12, 4)
        )
        account_actions = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        account_actions.pack(fill="x", padx=16, pady=4)
        StyledButton(account_actions, text="Edytuj", secondary=True, command=self.edit_account).pack(
            side="left", fill="x", expand=True, padx=(0, 4)
        )
        StyledButton(account_actions, text="Usuń", danger=True, command=self.delete_account).pack(
            side="left", fill="x", expand=True, padx=(4, 0)
        )
        StyledButton(self.sidebar, text="Połączenie API", secondary=True, command=self.open_api_settings).pack(
            fill="x", padx=16, pady=4
        )
        StyledButton(
            self.sidebar, text="Podsumowanie", secondary=True, command=self.open_session_summary
        ).pack(fill="x", padx=16, pady=4)
        StyledButton(
            self.sidebar, text="Kalendarz", secondary=True, command=self.open_activity_calendar
        ).pack(fill="x", padx=16, pady=4)
        StyledButton(
            self.sidebar, text="Ukryj obok zegara", secondary=True, command=self.minimize_to_tray
        ).pack(fill="x", padx=16, pady=4)
        StyledButton(
            self.sidebar, text="Aktualizacje", secondary=True, command=self.open_update_settings
        ).pack(fill="x", padx=16, pady=4)
        StyledButton(
            self.sidebar, text="O aplikacji", secondary=True, command=self.open_about
        ).pack(fill="x", padx=16, pady=4)
        self.api_state_label = tk.Label(
            self.sidebar, text="", bg=COLORS["sidebar"], fg=COLORS["muted"], font=("Segoe UI", 8)
        )
        self.api_state_label.pack(anchor="w", padx=20, pady=(5, 0))

        safety = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        safety.pack(side="bottom", fill="x", padx=18, pady=18)
        self.monitor_dot = tk.Label(safety, text="●", bg=COLORS["sidebar"], fg=COLORS["green"], font=("Segoe UI", 10))
        self.monitor_dot.pack(side="left")
        tk.Label(
            safety, text=" Monitor klienta aktywny", bg=COLORS["sidebar"], fg=COLORS["muted"], font=("Segoe UI", 9)
        ).pack(side="left")

        self.main = tk.Frame(self, bg=COLORS["bg"])
        self.main.pack(side="left", fill="both", expand=True)

        top = tk.Frame(self.main, bg=COLORS["bg"])
        top.pack(fill="x", padx=24, pady=(22, 12))
        title_box = tk.Frame(top, bg=COLORS["bg"])
        title_box.pack(side="left", fill="x", expand=True)
        self.account_title = tk.Label(
            title_box, text="", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI Semibold", 22)
        )
        self.account_title.pack(anchor="w")
        self.account_subtitle = tk.Label(
            title_box, text="", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 10)
        )
        self.account_subtitle.pack(anchor="w", pady=(2, 0))

        StyledButton(top, text="Odczytaj klienta", secondary=True, command=self.sync_client).pack(side="right", padx=(8, 0))
        StyledButton(top, text="Importuj mecz", secondary=True, command=self.import_latest_match).pack(side="right", padx=(8, 0))
        StyledButton(top, text="+ Dodaj grę", command=self.add_game).pack(side="right")

        self.summary = Card(self.main)
        self.summary.pack(fill="x", padx=24, pady=(0, 12))
        summary_left = tk.Frame(self.summary, bg=COLORS["card"])
        summary_left.pack(side="left", fill="both", expand=True, padx=20, pady=16)
        self.level_label = tk.Label(
            summary_left, text="", bg=COLORS["card"], fg=COLORS["gold"], font=("Segoe UI Semibold", 18)
        )
        self.level_label.pack(anchor="w")
        self.xp_label = tk.Label(
            summary_left, text="", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 10)
        )
        self.xp_label.pack(anchor="w", pady=(4, 6))
        self.progress = ttk.Progressbar(summary_left, style="XP.Horizontal.TProgressbar", maximum=100)
        self.progress.pack(fill="x", pady=(0, 2), ipady=3)

        self.stat_labels: dict[str, tk.Label] = {}
        stats_box = tk.Frame(self.summary, bg=COLORS["card"])
        stats_box.pack(side="right", padx=10, pady=12)
        for idx, (key, title) in enumerate(
            [("games", "GRY"), ("avg", "ŚR. XP"), ("winrate", "WIN RATE"), ("next", "DO 30 LVL")]
        ):
            cell = tk.Frame(stats_box, bg=COLORS["card"], width=105)
            cell.grid(row=0, column=idx, padx=9)
            cell.grid_propagate(False)
            label = tk.Label(cell, text="—", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 16))
            label.pack()
            tk.Label(cell, text=title, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI Semibold", 8)).pack(pady=(3, 0))
            self.stat_labels[key] = label

        # Keep feedback and row actions outside the expanding history card.  When
        # this bar was packed after the table, Windows could clip it completely
        # on shorter displays, hiding both status messages and edit controls.
        status_frame = tk.Frame(self.main, bg=COLORS["bg"])
        status_frame.pack(fill="x", padx=24, pady=(0, 12))
        self.status = tk.Label(
            status_frame, text="Gotowe", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 9)
        )
        self.status.pack(side="left")
        StyledButton(status_frame, text="Usuń wpis", secondary=True, command=self.delete_selected_game).pack(side="right", padx=(8, 0))
        StyledButton(status_frame, text="Edytuj wpis", secondary=True, command=self.edit_selected_game).pack(side="right")

        table_card = Card(self.main)
        table_card.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        table_head = tk.Frame(table_card, bg=COLORS["card"])
        table_head.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(
            table_head, text="Historia gier", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 14)
        ).pack(side="left")
        self.history_hint = tk.Label(
            table_head, text="Podwójne kliknięcie pokazuje szczegóły", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)
        )
        self.history_hint.pack(side="right")

        filters = tk.Frame(table_card, bg=COLORS["card"])
        filters.pack(fill="x", padx=16, pady=(0, 9))
        self.search_filter = tk.StringVar()
        self.result_filter = tk.StringVar(value="Wszystkie wyniki")
        self.queue_filter = tk.StringVar(value="Wszystkie tryby")
        self.date_filter = tk.StringVar(value="Cała historia")
        tk.Label(
            filters, text="Szukaj:", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)
        ).pack(side="left", padx=(0, 5))
        search_entry = tk.Entry(
            filters, textvariable=self.search_filter, bg=COLORS["input"], fg=COLORS["text"],
            insertbackground=COLORS["text"], relief="flat", font=("Segoe UI", 9), width=20,
        )
        search_entry.pack(side="left", ipady=6, padx=(0, 7))
        search_entry.insert(0, "")
        search_entry.bind("<KeyRelease>", lambda _event: self._refresh_content())
        self.result_filter_combo = ttk.Combobox(
            filters, textvariable=self.result_filter,
            values=["Wszystkie wyniki", "Wygrane", "Przegrane"], state="readonly", width=16,
        )
        self.result_filter_combo.pack(side="left", padx=4, ipady=3)
        self.result_filter_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_content())
        self.queue_filter_combo = ttk.Combobox(
            filters, textvariable=self.queue_filter, values=["Wszystkie tryby"], state="readonly", width=18,
        )
        self.queue_filter_combo.pack(side="left", padx=4, ipady=3)
        self.queue_filter_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_content())
        self.date_filter_combo = ttk.Combobox(
            filters, textvariable=self.date_filter,
            values=["Cała historia", "Dzisiaj", "Ostatnie 7 dni", "Ostatnie 30 dni"],
            state="readonly", width=17,
        )
        self.date_filter_combo.pack(side="left", padx=4, ipady=3)
        self.date_filter_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_content())
        StyledButton(filters, text="Wyczyść", secondary=True, command=self.clear_filters).pack(side="right")

        columns = ("date", "champion", "result", "kda", "cs", "mode", "duration", "gain", "after")
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse")
        headings = {
            "date": "DATA", "champion": "BOHATER", "result": "WYNIK", "kda": "K / D / A",
            "cs": "CS", "mode": "TRYB", "duration": "CZAS", "gain": "+XP", "after": "STAN PO GRZE"
        }
        widths = {"date": 125, "champion": 105, "result": 75, "kda": 85, "cs": 50, "mode": 125, "duration": 60, "gain": 65, "after": 115}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], minwidth=45, anchor="w", stretch=column in ("date", "champion", "mode"))
        self.tree.tag_configure("win", foreground=COLORS["green"])
        self.tree.tag_configure("loss", foreground=COLORS["red"])
        self.tree.tag_configure("unknown", foreground=COLORS["muted"])
        self.tree.bind("<Double-1>", lambda _event: self.show_selected_game_details())
        self.tree.bind("<Delete>", lambda _event: self.delete_selected_game())
        scrollbar = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(0, 16))
        scrollbar.pack(side="right", fill="y", padx=(0, 12), pady=(0, 16))

    def _close(self) -> None:
        self.exit_app()

    def minimize_to_tray(self) -> None:
        if pystray is None or Image is None or ImageDraw is None:
            if messagebox.askyesno(
                "Brak obsługi zasobnika",
                "Nie udało się uruchomić ikony obok zegara. Zakończyć tracker?",
                parent=self,
            ):
                self.exit_app()
            return
        if self.tray_icon is None:
            icon_image = Image.new("RGBA", (64, 64), COLORS["sidebar"])
            draw = ImageDraw.Draw(icon_image)
            draw.rounded_rectangle((5, 5, 59, 59), radius=12, fill=COLORS["card_alt"], outline=COLORS["gold"], width=4)
            draw.text((22, 14), "L", fill=COLORS["gold"], stroke_width=1)
            menu = pystray.Menu(
                pystray.MenuItem("Otwórz tracker", lambda _icon, _item: self.after(0, self.restore_from_tray), default=True),
                pystray.MenuItem("Podsumowanie", lambda _icon, _item: self.after(0, self._open_summary_from_tray)),
                pystray.MenuItem("Zakończ", lambda _icon, _item: self.after(0, self.exit_app)),
            )
            self.tray_icon = pystray.Icon("lol_xp_tracker", icon_image, "LoL XP Tracker", menu)
            self.tray_icon.run_detached()
        self.withdraw()

    def restore_from_tray(self) -> None:
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()

    def _open_summary_from_tray(self) -> None:
        self.restore_from_tray()
        self.open_session_summary()

    def exit_app(self) -> None:
        self._closing = True
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
        self.destroy()

    def set_status(self, text: str, color: str | None = None) -> None:
        self.status.configure(text=text, fg=color or COLORS["muted"])

    def current_account(self) -> sqlite3.Row | None:
        return self.db.get_account(self.selected_account_id) if self.selected_account_id else None

    def refresh_all(self) -> None:
        self._refresh_accounts()
        self._refresh_content()
        self.refresh_api_state()

    def refresh_api_state(self) -> None:
        backend_url = self.db.get_setting("backend_url")
        access_token = self.db.get_setting("backend_access_token")
        local_key = self.db.get_setting("riot_api_key")
        state = self.db.get_setting("riot_api_state", "unknown")
        if bool(backend_url) != bool(access_token):
            text, color = "SERWER: uzupełnij ustawienia", COLORS["red"]
        elif backend_url and access_token:
            states = {
                "ok": ("SERWER: połączenie działa", COLORS["green"]),
                "access_error": ("SERWER: sprawdź kod dostępu", COLORS["red"]),
                "server_key_expired": ("SERWER: właściciel musi zmienić klucz Riot", COLORS["red"]),
                "backend_unavailable": ("SERWER: chwilowo niedostępny", COLORS["gold"]),
            }
            text, color = states.get(state, ("SERWER: skonfigurowany", COLORS["teal"]))
        elif not local_key:
            text, color = "API: brak konfiguracji", COLORS["muted"]
        else:
            if state == "expired":
                text, color = "API: klucz wygasł", COLORS["red"]
            elif state == "ok":
                text, color = "API: połączenie działa", COLORS["green"]
            else:
                text, color = "API: klucz zapisany", COLORS["gold"]
        self.api_state_label.configure(text=text, fg=color)

    def match_api_configured(self) -> bool:
        backend_ready = bool(
            self.db.get_setting("backend_url")
            and self.db.get_setting("backend_access_token")
        )
        return backend_ready or bool(self.db.get_setting("riot_api_key"))

    def match_api_client(self, platform: str) -> RiotApiClient:
        backend_url = self.db.get_setting("backend_url")
        access_token = self.db.get_setting("backend_access_token")
        if backend_url and access_token:
            client_instance_id = self.db.get_setting("client_instance_id")
            if not client_instance_id:
                client_instance_id = secrets.token_urlsafe(24)
                self.db.set_setting("client_instance_id", client_instance_id)
            return RiotApiClient(
                "",
                platform,
                backend_url=backend_url,
                access_token=access_token,
                client_instance_id=client_instance_id,
            )
        return RiotApiClient(self.db.get_setting("riot_api_key"), platform)

    def remember_api_error(self, error: RiotApiError) -> None:
        if error.code == "access_denied":
            state = "access_error"
        elif error.code == "riot_key_expired":
            state = "server_key_expired" if self.db.get_setting("backend_url") else "expired"
        elif error.code == "backend_unavailable":
            state = "backend_unavailable"
        else:
            return
        self.db.set_setting("riot_api_state", state)
        self.refresh_api_state()

    def _refresh_accounts(self) -> None:
        for child in self.accounts_frame.winfo_children():
            child.destroy()
        accounts = self.db.list_accounts()
        if accounts and not self.selected_account_id:
            self.selected_account_id = int(accounts[0]["id"])
        for account in accounts:
            active = int(account["id"]) == self.selected_account_id
            button = tk.Button(
                self.accounts_frame,
                text=f"{account['game_name']}#{account['tag_line']}\nPoziom {account['current_level']}  •  {account['platform']}",
                command=lambda account_id=int(account["id"]): self.select_account(account_id),
                anchor="w",
                justify="left",
                bg="#19263d" if active else COLORS["sidebar"],
                fg=COLORS["text"] if active else COLORS["muted"],
                activebackground="#20304c",
                activeforeground=COLORS["text"],
                relief="flat",
                bd=0,
                padx=12,
                pady=9,
                cursor="hand2",
                font=("Segoe UI", 9),
            )
            button.pack(fill="x", pady=2)

    def _refresh_content(self) -> None:
        account = self.current_account()
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not account:
            self.account_title.configure(text="Dodaj pierwsze konto")
            self.account_subtitle.configure(text="Historia każdego konta będzie przechowywana osobno.")
            return

        self.account_title.configure(text=f"{account['game_name']}#{account['tag_line']}")
        self.account_subtitle.configure(text=f"Serwer {account['platform']}  •  dane przechowywane lokalnie")
        self.level_label.configure(text=f"Poziom {account['current_level']}")
        if account["xp_required"]:
            self.xp_label.configure(text=f"{account['current_xp']:,} / {account['xp_required']:,} XP".replace(",", " "))
            self.progress["value"] = progress_percent(account["current_xp"], account["xp_required"])
        else:
            self.xp_label.configure(text=f"{account['current_xp']:,} XP  •  odczytaj klienta, aby poznać rozmiar paska".replace(",", " "))
            self.progress["value"] = 0

        stats = self.db.stats(int(account["id"]))
        average = float(stats["avg_xp"] or 0)
        decided = int(stats["decided"] or 0)
        wins = int(stats["wins"] or 0)
        estimate = games_to_level_30(
            int(account["current_level"]), int(account["current_xp"]),
            int(account["xp_required"]), average,
        )
        self.stat_labels["games"].configure(text=str(stats["games"]))
        self.stat_labels["avg"].configure(text=f"{average:.0f}" if average else "—")
        self.stat_labels["winrate"].configure(text=f"{wins / decided * 100:.0f}%" if decided else "—")
        self.stat_labels["next"].configure(text=str(estimate) if estimate is not None else "—")

        queue_names = ["Wszystkie tryby", *self.db.queue_names(int(account["id"]))]
        self.queue_filter_combo.configure(values=queue_names)
        if self.queue_filter.get() not in queue_names:
            self.queue_filter.set("Wszystkie tryby")
        result_map = {"Wszystkie wyniki": "all", "Wygrane": "win", "Przegrane": "loss"}
        date_map = {"Cała historia": "all", "Dzisiaj": "today", "Ostatnie 7 dni": "7d", "Ostatnie 30 dni": "30d"}
        queue_value = "all" if self.queue_filter.get() == "Wszystkie tryby" else self.queue_filter.get()
        games = self.db.list_games_filtered(
            int(account["id"]),
            search=self.search_filter.get(),
            result=result_map.get(self.result_filter.get(), "all"),
            queue_name=queue_value,
            date_scope=date_map.get(self.date_filter.get(), "all"),
        )
        for game in games:
            if game["win"] == 1:
                result, tag = "Wygrana", "win"
            elif game["win"] == 0:
                result, tag = "Przegrana", "loss"
            else:
                result, tag = "—", "unknown"
            gain = f"+{game['xp_gained']}" if game["xp_gained"] is not None else "—"
            after = f"Lv {game['level_after']} • {game['xp_after']} XP"
            self.tree.insert(
                "", "end", iid=str(game["id"]),
                values=(
                    format_date(game["played_at"]), game["champion"], result,
                    f"{game['kills']} / {game['deaths']} / {game['assists']}", game["cs"],
                    game["queue_name"], format_duration(game["duration_seconds"]), gain, after,
                ),
                tags=(tag,),
            )

    def select_account(self, account_id: int) -> None:
        self.selected_account_id = account_id
        self.refresh_all()

    def clear_filters(self) -> None:
        self.search_filter.set("")
        self.result_filter.set("Wszystkie wyniki")
        self.queue_filter.set("Wszystkie tryby")
        self.date_filter.set("Cała historia")
        self._refresh_content()

    def add_account(self, initial: dict[str, Any] | None = None) -> None:
        AccountDialog(self, initial=initial)

    def edit_account(self) -> None:
        account = self.current_account()
        if account:
            AccountDialog(self, account=account)

    def delete_account(self) -> None:
        account = self.current_account()
        if not account:
            return
        if not messagebox.askyesno(
            "Usuń konto",
            f"Usunąć {account['game_name']}#{account['tag_line']} razem z całą jego historią?",
            parent=self,
        ):
            return
        self.db.delete_account(int(account["id"]))
        accounts = self.db.list_accounts()
        self.selected_account_id = int(accounts[0]["id"]) if accounts else None
        self.refresh_all()

    def add_game(self, initial: dict[str, Any] | None = None) -> None:
        account = self.current_account()
        if not account:
            messagebox.showinfo("Brak konta", "Najpierw dodaj konto.", parent=self)
            return
        GameDialog(self, account, initial)

    def selected_game_id(self) -> int | None:
        selection = self.tree.selection()
        return int(selection[0]) if selection else None

    def edit_selected_game(self) -> None:
        account = self.current_account()
        game_id = self.selected_game_id()
        if not account or game_id is None:
            self.set_status("Zaznacz wpis, który chcesz edytować.", COLORS["gold"])
            return
        self.edit_game_by_id(game_id)

    def edit_game_by_id(self, game_id: int) -> None:
        account = self.current_account()
        if not account:
            return
        game = self.db.get_game(game_id, int(account["id"]))
        if game:
            GameDialog(self, account, game, game_id=game_id)

    def show_selected_game_details(self) -> None:
        account = self.current_account()
        game_id = self.selected_game_id()
        if not account or game_id is None:
            return
        game = self.db.get_game(game_id, int(account["id"]))
        if game:
            MatchDetailsDialog(self, account, game)

    def refresh_game_details(self, game_id: int) -> None:
        account = self.current_account()
        if not account:
            return
        game = self.db.get_game(game_id, int(account["id"]))
        if not game or not game["match_id"]:
            messagebox.showinfo(
                "Brak identyfikatora meczu",
                "Tego wpisu nie można automatycznie uzupełnić, ponieważ nie ma identyfikatora Riot.",
                parent=self,
            )
            return
        if not self.match_api_configured():
            ApiSettingsDialog(self)
            return
        self.set_status("Pobieram pełne szczegóły meczu z Riot…", COLORS["gold"])

        def task() -> dict[str, Any]:
            client = self.match_api_client(account["platform"])
            return client.match_by_id(
                account["game_name"], account["tag_line"], game["match_id"]
            )

        def success(data: dict[str, Any]) -> None:
            self.db.enrich_game_details(game_id, int(account["id"]), data)
            self.db.set_setting("riot_api_state", "ok")
            self.refresh_all()
            self.set_status("Uzupełniono brakujące szczegóły meczu.", COLORS["green"])
            refreshed = self.db.get_game(game_id, int(account["id"]))
            if refreshed:
                MatchDetailsDialog(self, self.db.get_account(int(account["id"])), refreshed)

        self._run_background(task, success)

    def delete_selected_game(self) -> None:
        account = self.current_account()
        game_id = self.selected_game_id()
        if not account or game_id is None:
            self.set_status("Zaznacz wpis, który chcesz usunąć.", COLORS["gold"])
            return
        if messagebox.askyesno("Usuń wpis", "Na pewno usunąć wybraną grę z historii?", parent=self):
            self.db.delete_game(game_id, int(account["id"]))
            self.refresh_all()

    def open_api_settings(self) -> None:
        ApiSettingsDialog(self)

    def open_session_summary(self) -> None:
        account = self.current_account()
        if account:
            SessionDialog(self, account)

    def open_activity_calendar(self) -> None:
        account = self.current_account()
        if account:
            ActivityCalendarDialog(self, account)

    def open_update_settings(self) -> None:
        UpdateSettingsDialog(self)

    def open_about(self) -> None:
        AboutDialog(self)

    def check_updates(self, silent: bool = False) -> None:
        manifest_url = self.db.get_setting("update_manifest_url", DEFAULT_MANIFEST_URL)
        if not manifest_url:
            if not silent:
                UpdateSettingsDialog(self)
            return
        if not silent:
            self.set_status("Sprawdzam dostępność aktualizacji…", COLORS["gold"])

        def task():
            return check_for_update(manifest_url, __version__)

        def success(info):
            if info is None:
                if not silent:
                    messagebox.showinfo(
                        "Aktualizacje", f"Masz najnowszą wersję ({__version__}).", parent=self
                    )
                    self.set_status("Aplikacja jest aktualna.", COLORS["green"])
                return
            notes = f"\n\n{info.notes}" if info.notes else ""
            if messagebox.askyesno(
                "Dostępna aktualizacja",
                f"Dostępna jest wersja {info.version}. Pobrać i zainstalować?{notes}",
                parent=self,
            ):
                self._download_update(info)
            else:
                self.set_status(f"Dostępna wersja {info.version}.", COLORS["gold"])

        self._run_background(task, success, quiet=silent)

    def _download_update(self, info) -> None:
        self.set_status(f"Pobieram wersję {info.version}…", COLORS["gold"])
        if getattr(sys, "frozen", False):
            app_directory = Path(sys.executable).resolve().parent
        else:
            app_directory = Path(__file__).resolve().parents[1]

        def task():
            return prepare_update(info, app_directory)

        def success(script: Path):
            try:
                launch_prepared_update(script)
            except UpdateError as error:
                messagebox.showerror("Aktualizacja nieudana", str(error), parent=self)
                return
            self.exit_app()

        self._run_background(task, success)

    def _run_background(
        self,
        task: Callable[[], Any],
        success: Callable[[Any], None],
        *,
        quiet: bool = False,
    ) -> None:
        if self.busy and not quiet:
            return
        if not quiet:
            self.busy = True
        def runner() -> None:
            try:
                result = task()
            except Exception as error:  # transported to UI thread
                if not self._closing:
                    # Exception targets are cleared when an ``except`` block
                    # ends.  Bind both values now so Tk can safely execute the
                    # callback after the worker thread has left this block.
                    self.after(
                        0,
                        lambda caught_error=error, is_quiet=quiet: self._background_error(
                            caught_error, is_quiet
                        ),
                    )
            else:
                if not self._closing:
                    self.after(0, lambda: self._background_success(success, result, quiet))
        threading.Thread(target=runner, daemon=True).start()

    def _background_success(self, callback: Callable[[Any], None], result: Any, quiet: bool) -> None:
        if not quiet:
            self.busy = False
        callback(result)

    def _background_error(self, error: Exception, quiet: bool) -> None:
        if isinstance(error, RiotApiError):
            self.remember_api_error(error)
        if not quiet:
            self.busy = False
            self.set_status(str(error), COLORS["red"])
            messagebox.showerror("Nie udało się", str(error), parent=self)

    def import_latest_match(self) -> None:
        account = self.current_account()
        if not account:
            return
        if not self.match_api_configured():
            ApiSettingsDialog(self)
            return
        self.set_status("Pobieram ostatni mecz z API Riot…", COLORS["gold"])
        def task() -> dict[str, Any]:
            client = self.match_api_client(account["platform"])
            return client.latest_match(account["game_name"], account["tag_line"])
        def success(data: dict[str, Any]) -> None:
            self.db.set_setting("riot_api_state", "ok")
            self.refresh_api_state()
            if data.get("match_id") and self.db.match_exists(int(account["id"]), data["match_id"]):
                messagebox.showinfo("Mecz już zapisany", "Ostatni mecz tego konta znajduje się już w historii.", parent=self)
                self.set_status("Mecz jest już zapisany.")
                return
            self.set_status("Pobrano mecz. Uzupełnij lub odczytaj XP.", COLORS["green"])
            GameDialog(self, self.db.get_account(int(account["id"])), data)
        self._run_background(task, success)

    def sync_client(self) -> None:
        self.set_status("Łączę się z uruchomionym klientem LoL…", COLORS["gold"])
        self._run_background(lambda: LcuClient().current_summoner(), self._handle_manual_snapshot)

    def _handle_manual_snapshot(self, snapshot: dict[str, Any]) -> None:
        account = self.db.find_account(snapshot["game_name"], snapshot["tag_line"])
        if not account:
            if messagebox.askyesno(
                "Nowe konto",
                f"W kliencie jest zalogowane {snapshot['game_name']}#{snapshot['tag_line']}. Dodać je do trackera?",
                parent=self,
            ):
                self.add_account(initial=snapshot)
            return
        self.selected_account_id = int(account["id"])
        gain = calculate_xp_gain(
            int(account["current_level"]), int(account["current_xp"]), int(account["xp_required"]),
            int(snapshot["level"]), int(snapshot["xp"])
        )
        progressed = snapshot["level"] > account["current_level"] or (
            snapshot["level"] == account["current_level"] and snapshot["xp"] > account["current_xp"]
        )
        if progressed:
            initial = {
                "champion": "",
                "level_after": snapshot["level"],
                "xp_after": snapshot["xp"],
                "xp_required_after": snapshot["xp_required"],
                "xp_gained": gain,
                "notes": "XP odczytane z klienta LoL",
                "source": "lcu",
            }
            self.set_status("Wykryto nowe XP. Uzupełnij dane gry.", COLORS["green"])
            self.refresh_all()
            GameDialog(self, self.db.get_account(int(account["id"])), initial)
        else:
            self.db.update_account_progress(
                int(account["id"]), int(snapshot["level"]), int(snapshot["xp"]), int(snapshot["xp_required"])
            )
            self.refresh_all()
            self.set_status("Poziom i XP zsynchronizowano z klientem LoL.", COLORS["green"])

    def _poll_client(self) -> None:
        if self._closing:
            return
        if not self.poll_busy:
            self.poll_busy = True
            def runner() -> None:
                try:
                    snapshot = LcuClient().current_summoner()
                except Exception:
                    snapshot = None
                if not self._closing:
                    self.after(0, lambda: self._finish_poll(snapshot))
            threading.Thread(target=runner, daemon=True).start()
        self.after(15000, self._poll_client)

    def _finish_poll(self, snapshot: dict[str, Any] | None) -> None:
        self.poll_busy = False
        if not snapshot:
            self.monitor_dot.configure(fg=COLORS["muted"])
            return
        self.monitor_dot.configure(fg=COLORS["green"])
        account = self.db.find_account(snapshot["game_name"], snapshot["tag_line"])
        if not account:
            identity = f"{snapshot['game_name']}#{snapshot['tag_line']}".casefold()
            if snapshot["game_name"] and snapshot["tag_line"] and identity not in self.unknown_account_prompted:
                self.unknown_account_prompted.add(identity)
                if messagebox.askyesno(
                    "Wykryto nowe konto",
                    f"Zalogowano się jako {snapshot['game_name']}#{snapshot['tag_line']}. Dodać to konto do trackera?",
                    parent=self,
                ):
                    accounts = self.db.list_accounts()
                    fallback_platform = accounts[0]["platform"] if accounts else "EUW1"
                    try:
                        account_id = self.db.add_account(
                            snapshot["game_name"], snapshot["tag_line"],
                            snapshot.get("platform") or fallback_platform,
                            snapshot["level"], snapshot["xp"], snapshot["xp_required"],
                        )
                    except sqlite3.IntegrityError:
                        return
                    self.selected_account_id = account_id
                    self.refresh_all()
                    self.set_status("Automatycznie dodano konto wykryte w kliencie LoL.", COLORS["green"])
                    Toast(
                        self, "Dodano nowe konto",
                        f"{snapshot['game_name']}#{snapshot['tag_line']} • poziom {snapshot['level']}",
                    )
            return
        progressed = snapshot["level"] > account["current_level"] or (
            snapshot["level"] == account["current_level"] and snapshot["xp"] > account["current_xp"]
        )
        if not progressed:
            # Keep the bar limit in sync even when XP itself has not changed.
            # This also repairs values written by tracker versions before 0.3.
            if (
                snapshot["level"] == account["current_level"]
                and snapshot["xp"] == account["current_xp"]
                and snapshot["xp_required"] != account["xp_required"]
            ):
                self.db.update_account_progress(
                    int(account["id"]), snapshot["level"], snapshot["xp"], snapshot["xp_required"]
                )
                if int(account["id"]) == self.selected_account_id:
                    self.refresh_all()
            return

        gain = calculate_xp_gain(
            int(account["current_level"]), int(account["current_xp"]), int(account["xp_required"]),
            int(snapshot["level"]), int(snapshot["xp"])
        )
        if self.match_api_configured():
            def task() -> dict[str, Any]:
                try:
                    data = self.match_api_client(account["platform"]).latest_match(
                        account["game_name"], account["tag_line"]
                    )
                except RiotApiError as error:
                    data = {
                        "champion": "Do uzupełnienia",
                        "queue_name": "Nieznany",
                        "notes": f"XP zapisane automatycznie; API Riot: {error}",
                        "source": "auto_lcu",
                        "api_error": str(error),
                        "api_error_code": error.status_code,
                        "api_error_kind": error.code,
                    }
                data.update({
                    "level_after": snapshot["level"], "xp_after": snapshot["xp"],
                    "xp_required_after": snapshot["xp_required"], "xp_gained": gain,
                })
                if data.get("champion") != "Do uzupełnienia":
                    data.update({"notes": "Automatycznie wykryte po grze", "source": "auto"})
                return data
            def success(data: dict[str, Any]) -> None:
                if data.get("api_error"):
                    self.remember_api_error(
                        RiotApiError(
                            str(data["api_error"]),
                            status_code=data.get("api_error_code"),
                            code=str(data.get("api_error_kind") or "api_error"),
                        )
                    )
                elif not data.get("api_error"):
                    self.db.set_setting("riot_api_state", "ok")
                self.refresh_api_state()
                if data.get("match_id") and self.db.match_exists(int(account["id"]), data["match_id"]):
                    self.db.update_match_progress(
                        int(account["id"]), data["match_id"], snapshot["level"], snapshot["xp"],
                        snapshot["xp_required"], gain
                    )
                else:
                    self.db.add_game(int(account["id"]), data)
                self.selected_account_id = int(account["id"])
                self.refresh_all()
                if data.get("champion") == "Do uzupełnienia":
                    self.set_status("Zapisano XP. Klucz API wymaga sprawdzenia, a statystyki uzupełnienia.", COLORS["gold"])
                    Toast(
                        self,
                        "Zapisano zdobyte XP",
                        f"+{gain if gain is not None else '?'} XP • uzupełnij statystyki i sprawdź klucz API",
                        COLORS["gold"],
                    )
                else:
                    self.set_status("Automatycznie zapisano zakończoną grę i zdobyte XP.", COLORS["green"])
                    result = "Wygrana" if data.get("win") else "Przegrana"
                    Toast(
                        self,
                        "Mecz zapisany automatycznie",
                        f"{data.get('champion', 'Nieznany')} • {result} • +{gain if gain is not None else '?'} XP",
                    )
            self._run_background(task, success, quiet=True)
        else:
            placeholder = {
                "champion": "Do uzupełnienia",
                "queue_name": "Nieznany",
                "level_after": snapshot["level"],
                "xp_after": snapshot["xp"],
                "xp_required_after": snapshot["xp_required"],
                "xp_gained": gain,
                "notes": "Automatycznie zapisane XP; uzupełnij statystyki gry",
                "source": "auto_lcu",
            }
            self.db.add_game(int(account["id"]), placeholder)
            self.selected_account_id = int(account["id"])
            self.refresh_all()
            self.set_status("Zapisano XP. Uzupełnij statystyki ostatniej gry.", COLORS["gold"])
            Toast(
                self,
                "Zapisano zdobyte XP",
                f"+{gain if gain is not None else '?'} XP • uzupełnij statystyki ostatniej gry",
                COLORS["gold"],
            )
