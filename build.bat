@echo off
echo ===============================
echo   Build Sistem Mikrotik Invoice
echo ===============================

REM Hapus folder build lama
rmdir /s /q build
rmdir /s /q dist
del main.spec

REM Compile pakai PyInstaller
pyinstaller --onedir --noconsole ^
  --icon=assets\icon.ico ^
  --add-data "assets;assets" ^
  --add-data "assets\JetBrainsMono-Bold.ttf;assets" ^
  --add-data "assets\JetBrainsMono-Regular.ttf;assets" ^
  --add-data "config.json;." ^
  --add-data "poppler\Library\bin;poppler\bin" ^
  --add-data "assets\logo.bmp;assets" ^
  --add-data "assets\qris.png;assets" ^
  main.py

echo.
echo ===============================
echo   Build selesai!
echo File ada di folder dist\main.exe
echo.
pause
