@echo off
cd /d "%~dp0"
python -c "import pystray, PIL" >nul 2>nul
if errorlevel 1 (
  echo Pierwsze uruchomienie - instaluje obsluge zasobnika systemowego...
  python -m pip install -r requirements.txt
)
python app.py
if errorlevel 1 (
  echo.
  echo Nie udalo sie uruchomic aplikacji. Sprawdz, czy Python jest zainstalowany.
  pause
)
