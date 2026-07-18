# Prywatny backend LoL XP Tracker

Cloudflare Worker ukrywa klucz Riot API przed aplikacjami desktopowymi. Wersja 0.10 zawiera panel zarządzania 2.0, bezterminowe profile znajomych, automatyczne dopisywanie Riot ID oraz alerty kont i urządzeń.

## Jak działa dostęp

- jeden znajomy otrzymuje jeden bezterminowy kod;
- każde konto użyte z prawidłowym kodem zostaje automatycznie przypisane do profilu znajomego;
- znajomy może korzystać z dowolnej liczby kont Riot bez oczekiwania na zgodę właściciela;
- nowe konto działa od razu, ale pozostaje czerwonym alertem do oznaczenia jako sprawdzone;
- kod działa do ręcznego wyłączenia albo zmiany przez właściciela;
- nowe urządzenie nie jest blokowane — zostaje dopuszczone i oznaczone czerwonym alertem;
- surowe kody i adresy IP nie są zapisywane;
- minimalny dziennik aktywności jest automatycznie czyszczony po 30 dniach.

Identyfikator urządzenia oznacza losowy identyfikator instalacji trackera, a nie sprzętowy fingerprint. Zwykłe przekazanie kodu innej osobie utworzy alert o nowym urządzeniu, ale system nie stanowi zabezpieczenia przed celowym skopiowaniem całego profilu aplikacji.

## Wdrożenie przez GitHub Actions

Repozytorium zawiera workflow **Deploy private backend**. Po scaleniu zmian backendu do gałęzi `main` testy i wdrożenie uruchamiają się automatycznie. Przycisk ręcznego uruchomienia pozostaje dostępny jako awaryjna możliwość ponowienia wdrożenia. Do GitHub Actions Secrets dodaj:

- `CLOUDFLARE_API_TOKEN` — token wdrożeniowy z uprawnieniami Workers Scripts Edit, D1 Edit oraz odczytem danych konta;
- `CLOUDFLARE_ACCOUNT_ID` — identyfikator konta Cloudflare.

Workflow sam utworzy bazę `lol-xp-tracker-access` w jurysdykcji UE, zastosuje migracje i podłączy ją jako `ACCESS_DB`.

W ustawieniach Workera `lol-xp-tracker-api` dodaj zaszyfrowane sekrety:

- `RIOT_API_KEY` — aktywny Development albo zatwierdzony Personal API Key;
- `ADMIN_TOKEN` — długi, losowy kod znany wyłącznie właścicielowi.

Bezpieczny `ADMIN_TOKEN` można wygenerować lokalnie:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Nie wpisuj `ADMIN_TOKEN` ani `RIOT_API_KEY` do repozytorium lub GitHub Actions Secrets. Są to sekrety uruchomionego Workera.

## Panel właściciela

Po wdrożeniu otwórz:

`https://ADRES-WORKERA.workers.dev/admin`

Zaloguj się wartością `ADMIN_TOKEN`. W panelu możesz:

- korzystać z osobnych widoków: pulpit, znajomi, konta Riot, urządzenia, aktywność i stan systemu;
- utworzyć znajomego i skopiować zaproszenie;
- przeglądać automatycznie dodane konta Riot i oznaczać je jako sprawdzone;
- dodawać oraz usuwać konta ręcznie;
- wyłączyć lub zmienić kod;
- zobaczyć nowe urządzenia, nazwać je i oznaczyć jako znane;
- filtrować ostatnią aktywność kodów i kontrolować stan Workera, D1 oraz konfiguracji.

Aplikacja desktopowa przyjmuje całe zaproszenie w oknie **Połączenie API**. Adres serwera i kod wypełnią się automatycznie.

## Zgodność ze starszą konfiguracją

Sekret `ACCESS_RULES` z wersji 0.7 jest nadal obsługiwany jako tryb zgodności. Dotychczasowy kod będzie działał podczas przechodzenia na profile z panelu. Nowych znajomych należy dodawać już w panelu; `ACCESS_RULES` można usunąć po wymianie wszystkich starych kodów.

## Uruchomienie lokalne

1. Skopiuj `.dev.vars.example` jako `.dev.vars` i wpisz testowe sekrety.
2. Uruchom `npm install` w folderze `backend`.
3. Zastosuj migracje lokalnie przez Wrangler.
4. Uruchom `npm run dev`.

Plik `.dev.vars` jest ignorowany przez Git i nie może zostać opublikowany.
