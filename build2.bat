@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

echo ===============================
echo  BUILD MIKROTIK INVOICE (SECURE)
echo ===============================

REM ===============================
REM  HAPUS BUILD LAMA
REM ===============================
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
rmdir /s /q obf 2>nul

REM ===============================
REM  OBFUSCATE SOURCE
REM ===============================
echo.
echo 🔐 Obfuscating source...

pyarmor gen -r main_app.py core web.py uninstall_guard.py secret_parts.py

IF ERRORLEVEL 1 (
    echo ❌ Obfuscate GAGAL
    pause
    exit /b 1
)

REM ===============================
REM  BUILD APLIKASI UTAMA
REM ===============================
echo.
echo 🔧 Build aplikasi utama...

pyinstaller ^
 --noconfirm ^
 --clean ^
 --onefile ^
 --noconsole ^
 --icon=static\icon.ico ^
 --splash static\splash.png ^
 --hidden-import pyi_splash ^
 --collect-all flask ^
 --collect-all schedule ^
 --collect-all dateutil ^
 --collect-all core ^
 --add-data "templates;templates" ^
 --add-data "static;static" ^
 --add-data "web.py;." ^
 --name mikrotik_invoice ^
 main_app.py



IF ERRORLEVEL 1 (
    echo ❌ Build aplikasi utama GAGAL
    pause
    exit /b 1
)

REM ===============================
REM  BUILD UNINSTALL GUARD
REM ===============================
echo.
echo 🔒 Build uninstall guard...

pyinstaller ^
 --noconfirm ^
 --clean ^
 --onefile ^
 --noconsole ^
 --icon=static\icon.ico ^
 --name uninstall_guard ^
 dist\uninstall_guard.py

IF ERRORLEVEL 1 (
    echo ❌ Build uninstall_guard GAGAL
    pause
    exit /b 1
)

echo.
echo ✅ BUILD SELESAI
echo 📦 File final ada di folder dist
pause
