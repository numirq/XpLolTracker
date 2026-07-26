@echo off
set "TCL_LIBRARY="
set "TK_LIBRARY="
set "_MEIPASS2="
set "_PYI_APPLICATION_HOME_DIR="
set "_PYI_ARCHIVE_FILE="
set "_PYI_PARENT_PROCESS_LEVEL="
set "_PYI_SPLASH_IPC="
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
