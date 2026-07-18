# Bezpieczeństwo

Nie umieszczaj klucza Riot API, lokalnej bazy danych ani danych logowania w issue, commicie lub pliku konfiguracyjnym repozytorium.

LoL XP Tracker przechowuje ustawienia i historię lokalnie w `%LOCALAPPDATA%\LoLXPTracker`. Repozytorium nie zawiera kluczy użytkowników ani ich baz SQLite.

Jeśli znajdziesz podatność, nie publikuj sekretów ani danych osobowych. Opisz problem w issue bez wrażliwych danych.

Klucz Riot dla prywatnej grupy powinien być zapisany wyłącznie jako secret Cloudflare Worker. Aplikacje desktopowe korzystają z osobnych kodów dostępu. Ujawniony kod znajomego można odwołać bez wymiany klucza Riot.
