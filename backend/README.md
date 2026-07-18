# Prywatny backend LoL XP Tracker

Cloudflare Worker ukrywa klucz Riot API przed aplikacjami desktopowymi. Przyjmuje wyłącznie odczyt ostatniego lub wskazanego meczu, wymaga osobnego kodu dostępu i ogranicza każdy kod do podanych Riot ID.

## Sekrety

- `RIOT_API_KEY` — aktywny Development lub zatwierdzony Personal API Key;
- `ACCESS_RULES` — obiekt JSON mapujący SHA-256 kodu znajomego na listę dozwolonych Riot ID.

Przykład struktury `ACCESS_RULES`:

```json
{
  "64_ZNAKI_SHA256_KODU": ["GameName#TagLine"]
}
```

Nigdy nie zapisuj prawdziwych wartości w repozytorium, logach ani pliku ZIP aplikacji.

## Wdrożenie przez GitHub Actions

Repozytorium zawiera ręczny workflow **Deploy private backend**. Do GitHub Actions Secrets dodaj:

- `CLOUDFLARE_API_TOKEN` — token wdrożeniowy Cloudflare;
- `CLOUDFLARE_ACCOUNT_ID` — identyfikator konta Cloudflare.

Następnie uruchom workflow z zakładki **Actions**. Po pierwszym wdrożeniu dodaj `RIOT_API_KEY` i `ACCESS_RULES` jako zaszyfrowane sekrety bezpośrednio w ustawieniach utworzonego Workera `lol-xp-tracker-api`.

Klucz Riot nie jest potrzebny workflow wdrożeniowemu i nie powinien być umieszczany w plikach repozytorium.

## Generowanie kodu znajomego

W głównym folderze projektu uruchom:

```powershell
python backend/generate_friend_token.py --account "GameName#TagLine"
```

Skrypt pokaże kod dla znajomego oraz fragment, który należy połączyć z istniejącym sekretem `ACCESS_RULES`.

## Uruchomienie lokalne

1. Skopiuj `.dev.vars.example` jako `.dev.vars` i wpisz testowe wartości.
2. Uruchom `npm install` w folderze `backend`.
3. Uruchom `npm run dev`.

Plik `.dev.vars` jest ignorowany przez Git i nie może zostać opublikowany.
