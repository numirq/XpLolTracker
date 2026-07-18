# LoL XP Tracker

Wersja 0.9.1

Desktopowy tracker poziomu konta League of Legends dla Windows. Obsługuje wiele kont i przechowuje ich historie osobno.

[Pobierz najnowszą wersję](https://github.com/numirq/XpLolTracker/releases/latest) · [Zgłoś problem](https://github.com/numirq/XpLolTracker/issues)

## Co potrafi

- zapisuje datę, bohatera, wynik, K/D/A, CS, obrażenia i czas meczu;
- zapisuje zdobyte XP, poziom i stan paska po meczu;
- obsługuje dowolną liczbę kont oraz serwerów Riot;
- odczytuje poziom i XP z uruchomionego klienta LoL;
- pobiera ostatni mecz przez oficjalne API Riot;
- automatycznie monitoruje klienta i zapisuje wykryty postęp;
- formularz gry dopasowuje się do mniejszych ekranów i ma przewijane pola;
- pokazuje dzienne i bieżące podsumowanie sesji;
- oblicza pozostałe XP oraz szacowaną liczbę gier do dowolnie wybranego poziomu;
- zestawia statystyki osobno dla każdego bohatera;
- pokazuje powiadomienie po automatycznym zapisaniu meczu;
- ostrzega, gdy zapisany klucz API Riot wygasł;
- filtruje historię po bohaterze, wyniku, trybie i zakresie dat;
- pokazuje osobne okno szczegółów meczu, w tym obrażenia, złoto i vision score;
- prezentuje miesięczny kalendarz aktywności z liczbą gier i XP;
- wykrywa nieznane konto zalogowane w kliencie i proponuje jego dodanie;
- może działać w zasobniku systemowym obok zegara;
- obsługuje bezpieczne aktualizacje z kontrolą SHA-256.
- pozwala uzupełnić szczegóły starszego meczu ponownym odczytem z API Riot;
- stosuje spójny ciemny wygląd również w rozwijanych listach Windows.
- zawiera widoczne informacje o prywatności, działaniu oraz niezależności produktu od Riot Games.
- pokazuje średnie XP, win rate i szacowaną liczbę gier do kolejnego poziomu;
- przechowuje dane lokalnie w bazie SQLite.
- może pobierać mecze przez prywatny Cloudflare Worker, dzięki czemu znajomi nie potrzebują własnych kluczy Riot API;
- używa osobnych, odwoływalnych kodów dostępu ograniczonych do wskazanych Riot ID.
- ma stały rozmiar głównego okna i zawsze widoczny pasek komunikatów oraz akcji historii.
- poprawnie pokazuje błędy połączenia odebrane przez zadania działające w tle.
- pozwala właścicielowi tworzyć bezterminowe profile znajomych z wieloma kontami Riot;
- przyjmuje zaproszenie do prywatnego serwera jednym wklejeniem;
- rejestruje nowe instalacje aplikacji bez blokowania dostępu i pokazuje alert w panelu właściciela;
- prowadzi oszczędny, 30-dniowy dziennik aktywności kodów bez zapisywania surowych adresów IP.
- pozwala ustawić dowolny przyszły cel poziomu osobno dla każdego konta; powyżej poziomu 30 wyliczenie XP jest wyraźnie oznaczone jako szacunkowe;
- pobiera i lokalnie buforuje oficjalne portrety bohaterów z Riot Data Dragon;
- pokazuje czytelny stan klienta: lobby, kolejkę, wybór bohatera, trwający i zakończony mecz;
- wysyła opcjonalne powiadomienia Windows po zapisaniu meczu oraz awansie;
- grupuje urządzenia pod właściwym znajomym, umożliwia wyszukiwanie, filtrowanie i zmianę nazwy profilu.

## Uruchomienie na Windows

1. Zainstaluj Python 3.11 lub nowszy z [python.org](https://www.python.org/downloads/). Podczas instalacji zaznacz **Add Python to PATH**.
2. Rozpakuj projekt.
3. Kliknij dwukrotnie `start.bat`.

Przy pierwszym uruchomieniu `start.bat` automatycznie zainstaluje małe dodatki potrzebne do ikony obok zegara.

Przy pierwszym uruchomieniu dodaj konto ręcznie albo użyj automatycznego wykrywania uruchomionego klienta League of Legends.

## Prywatny backend dla znajomych

Prywatny Cloudflare Worker z folderu [`backend`](backend) przechowuje klucz Riot jako sekret. Właściciel tworzy profil znajomego i wysyła jedno bezterminowe zaproszenie. Każde użyte później Riot ID zostaje automatycznie dopisane do właściwego profilu i działa od razu, a właściciel otrzymuje alert do sprawdzenia.

Nowe konto i nowa instalacja aplikacji nie są blokowane. Serwer dopuszcza żądanie, oznacza je czerwonym alertem i zapisuje zdarzenie w 30-dniowej historii aktywności. Panel 2.0 rozdziela pulpit, znajomych, konta, urządzenia, aktywność i stan systemu.

Instrukcja backendu i generator kodów znajdują się w [`backend/README.md`](backend/README.md).

## Lokalny tryb developerski

Do testowania bez prywatnego backendu można nadal użyć klucza z Riot Developer Portal:

1. Wejdź na [Riot Developer Portal](https://developer.riotgames.com/).
2. Zaloguj się i skopiuj wygenerowany klucz API.
3. W aplikacji wybierz **Połączenie API** i wklej klucz w opcjonalnym polu trybu developerskiego.

Klucz Development zwykle wygasa po 24 godzinach. Klucz nie jest dołączony do kodu; wpisana wartość pozostaje wyłącznie w lokalnej bazie aplikacji.

## Jak działa monitor

Co 15 sekund aplikacja sprawdza wyłącznie lokalny klient League of Legends. Jeśli wykryje wzrost XP na dodanym koncie:

- ze skonfigurowanym prywatnym backendem albo aktywnym kluczem lokalnym pobierze ostatni mecz i zapisze pełny wpis;
- bez dostępu do danych meczów zapisze XP oraz utworzy wpis „Do uzupełnienia”, który można otworzyć podwójnym kliknięciem.

Program nie klika w kliencie, nie rozpoczyna gier i nie steruje rozgrywką.
Lokalny odczyt XP zależy od interfejsu klienta Riot, dlatego po większej aktualizacji gry może wymagać poprawki.

## Zasobnik systemowy

Przycisk **Ukryj obok zegara** oraz zamknięcie głównego okna krzyżykiem pozostawiają tracker działający w tle. Kliknij ikonę trackera obok zegara, aby go przywrócić. Polecenie **Zakończ** w menu ikony całkowicie wyłącza program.

## Aktualizacje

Program korzysta z manifestu publikowanego w tym repozytorium i domyślnie sprawdza nowe wydania przy uruchomieniu. Przed instalacją paczka jest weryfikowana za pomocą SHA-256. Źródło można zmienić lub wyłączyć w oknie **Aktualizacje**.

## GitHub Releases

Każda zmiana numeru wersji w `lol_tracker/__init__.py` opublikowana na gałęzi `main` uruchamia testy i tworzy nowe wydanie GitHub. Workflow buduje paczkę ZIP, oblicza jej SHA-256 i aktualizuje `update-manifest.json` używany przez aplikację.

## Zbudowanie pliku EXE

Uruchom `build_exe.bat`. Skrypt zainstaluje PyInstaller i utworzy:

`dist/LoL-XP-Tracker.exe`

## Dane

Na Windows baza znajduje się w:

`%LOCALAPPDATA%\LoLXPTracker\tracker.db`

Warto co jakiś czas wykonać kopię tego pliku.

## Testy

W folderze projektu uruchom:

```powershell
python -m unittest discover -s tests -v
```
