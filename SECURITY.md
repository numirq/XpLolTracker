# Bezpieczeństwo

Nie umieszczaj klucza Riot API, lokalnej bazy danych ani danych logowania w issue, commicie lub pliku konfiguracyjnym repozytorium.

LoL XP Tracker przechowuje ustawienia i historię lokalnie w `%LOCALAPPDATA%\LoLXPTracker`. Repozytorium nie zawiera kluczy użytkowników ani ich baz SQLite.

Jeśli znajdziesz podatność, nie publikuj sekretów ani danych osobowych. Opisz problem w issue bez wrażliwych danych.

Klucz Riot dla prywatnej grupy powinien być zapisany wyłącznie jako secret Cloudflare Worker. Aplikacje desktopowe korzystają z osobnych kodów dostępu. Ujawniony kod znajomego można odwołać bez wymiany klucza Riot.

Kody znajomych są w bazie D1 przechowywane wyłącznie jako skróty SHA-256. Panel administracyjny pokazuje surowy kod tylko bezpośrednio po utworzeniu lub zmianie. Kod administratora jest sekretem Workera i nie może trafić do repozytorium.

Rejestr aktywności przechowuje identyfikator instalacji w postaci skrótu, przybliżony kraj, czas, konto i wynik żądania. Surowe adresy IP nie są zapisywane, a wpisy starsze niż 30 dni są automatycznie usuwane. Znajomych należy poinformować o takim rejestrowaniu aktywności przed przekazaniem kodu.
