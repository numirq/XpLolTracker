@echo off
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller -r requirements.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "LoL-XP-Tracker" app.py
echo.
echo Gotowe. Plik znajduje sie w folderze dist.
pause
