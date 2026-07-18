# Prywatny backend LoL XP Tracker

Cloudflare Worker ukrywa klucz Riot API przed aplikacjami desktopowymi. Wersja 0.8 dodaje panel właściciela, bezterminowe profile znajomych, wiele Riot ID w jednym profilu oraz alerty o nowych urządzeniach.

## Jak działa dostęp

- jeden znajomy otrzymuje jeden bezterminowy kod;
- jeżeli profil nie ma jeszcze konta, pierwsze konto użyte z zaproszeniem przypisze się automatycznie;
- do profilu można dodać dowolną liczbę kont Riot;
- kolejne konta dodaje właściciel w panelu, więc kod nie przejmie automatycznie dostępu do innego Riot ID;
- kod działa do ręcznego wyłączenia albo zmiany przez właściciela;
- nowe urządzenie nie jest blokowane — zostaje dopuszczone i oznaczone czerwonym alertem;
- surowe kody i adresy IP nie są zapisywane;
- minimalny dziennik aktywności jest automatycznie czyszczony po 30 dniach.

Identyfikator urządzenia oznacza losowy identyfikator instalacji trackera, a nie sprzętowy fingerprint. Zwykłe przekazanie kodu innej osobie utworzy alert o nowym urządzeniu, ale system nie stanowi zabezpieczenia przed celowym skopiowaniem całego profilu aplikacji.

## Wdrożenie przez GitHub Actions

Repozytorium zawiera ręczny workflow **Deploy private backend**. Do GitHub Actions Secrets dodaj:

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

- utworzyć znajomego i skopiować zaproszenie;
- dodawać oraz usuwać jego konta Riot;
- wyłączyć lub zmienić kod;
- zobaczyć nowe urządzenia, nazwać je i oznaczyć jako znane;
- przejrzeć ostatnią aktywność kodów.

Aplikacja desktopowa przyjmuje całe zaproszenie w oknie **Połączenie API**. Adres serwera i kod wypełnią się automatycznie.

## Zgodność ze starszą konfiguracją

Sekret `ACCESS_RULES` z wersji 0.7 jest nadal obsługiwany jako tryb zgodności. Dotychczasowy kod będzie działał podczas przechodzenia na profile z panelu. Nowych znajomych należy dodawać już w panelu; `ACCESS_RULES` można usunąć po wymianie wszystkich starych kodów.

## Uruchomienie lokalne

1. Skopiuj `.dev.vars.example` jako `.dev.vars` i wpisz testowe sekrety.
2. Uruchom `npm install` w folderze `backend`.
3. Zastosuj migracje lokalnie przez Wrangler.
4. Uruchom `npm run dev`.

Plik `.dev.vars` jest ignorowany przez Git i nie może zostać opublikowany.
