@echo off
title BUILD MIKROTIK INVOICE - WINDOWS 10
color 0A
setlocal EnableExtensions

cd /d "%~dp0"

set "VENV=%~dp0venv_win10"
set "PYTHON=%VENV%\Scripts\python.exe"
set "PYINSTALLER=%VENV%\Scripts\pyinstaller.exe"

echo.
echo ==========================================
echo   BUILD MIKROTIK INVOICE - WINDOWS 10
echo ==========================================
echo.

REM =========================================================
REM 1. CEK PYTHON
REM =========================================================
echo [1/8] Cek Python...

if not exist "%PYTHON%" (
echo.
echo [ERROR] Python venv_win10 tidak ditemukan:
echo %PYTHON%
echo.
pause
exit /b 1
)

"%PYTHON%" --version

if errorlevel 1 (
echo.
echo [ERROR] Python tidak bisa dijalankan.
echo.
pause
exit /b 1
)

REM =========================================================
REM 2. CEK PYINSTALLER
REM =========================================================
echo.
echo [2/8] Cek PyInstaller...

if not exist "%PYINSTALLER%" (
echo.
echo [ERROR] PyInstaller tidak ditemukan:
echo %PYINSTALLER%
echo.
echo Install dengan:
echo "%PYTHON%" -m pip install pyinstaller
echo.
pause
exit /b 1
)

"%PYINSTALLER%" --version

if errorlevel 1 (
echo.
echo [ERROR] PyInstaller gagal dijalankan.
echo.
pause
exit /b 1
)

REM =========================================================
REM 3. CEK FILE UTAMA
REM =========================================================
echo.
echo [3/8] Cek file utama...

if not exist "main_app.py" (
echo.
echo [ERROR] main_app.py tidak ditemukan.
echo.
pause
exit /b 1
)

echo [OK] main_app.py ditemukan.

REM =========================================================
REM 4. CEK FOLDER PENDUKUNG
REM =========================================================
echo.
echo [4/8] Cek folder pendukung...

if not exist "templates" (
echo [WARNING] Folder templates tidak ditemukan.
)

if not exist "static" (
echo [WARNING] Folder static tidak ditemukan.
)

if not exist "assets" (
echo [WARNING] Folder assets tidak ditemukan.
)

if not exist "core" (
echo [WARNING] Folder core tidak ditemukan.
)

if not exist "services" (
echo [WARNING] Folder services tidak ditemukan.
)

if not exist "poppler" (
echo [WARNING] Folder poppler tidak ditemukan.
)

REM =========================================================
REM 5. COMPILE CHECK
REM =========================================================
echo.
echo [5/8] Cek syntax main_app.py...

"%PYTHON%" -m py_compile main_app.py

if errorlevel 1 (
echo.
echo ==========================================
echo   [ERROR] main_app.py GAGAL COMPILE
echo ==========================================
echo.
pause
exit /b 1
)

echo [OK] main_app.py berhasil compile.

REM =========================================================
REM 6. TUTUP PROGRAM LAMA
REM =========================================================
echo.
echo [6/8] Menutup program lama...

taskkill /F /IM MikrotikInvoice_Win10.exe >nul 2>&1
taskkill /F /IM MikrotikInvoice.exe >nul 2>&1
taskkill /F /IM mikrotik_invoice.exe >nul 2>&1
taskkill /F /IM uninstall_guard.exe >nul 2>&1
taskkill /F /IM uninstall_guard_win10.exe >nul 2>&1

timeout /t 2 >nul

REM =========================================================
REM 7. BERSIHKAN BUILD LAMA
REM =========================================================
echo.
echo Membersihkan build lama...

if exist "build_win10" rmdir /S /Q "build_win10"
if exist "dist_win10" rmdir /S /Q "dist_win10"

echo.
echo ==========================================
echo   BUILD APLIKASI WINDOWS 10
echo ==========================================
echo.

"%PYINSTALLER%" ^
--clean ^
--noconfirm ^
--onedir ^
--windowed ^
--name "MikrotikInvoice_Win10" ^
--distpath "dist_win10" ^
--workpath "build_win10" ^
--icon "assets\icon.ico" ^
--paths "." ^
--collect-all ttkbootstrap ^
--collect-all PIL ^
--collect-all reportlab ^
--hidden-import=tkinter ^
--hidden-import=flask ^
--hidden-import=flask_sqlalchemy ^
--hidden-import=sqlalchemy ^
--hidden-import=jinja2 ^
--hidden-import=werkzeug ^
--hidden-import=itsdangerous ^
--hidden-import=click ^
--hidden-import=blinker ^
--hidden-import=schedule ^
--hidden-import=dotenv ^
--hidden-import=routeros_api ^
--hidden-import=win32print ^
--hidden-import=win32ui ^
--hidden-import=win32gui ^
--hidden-import=pythoncom ^
--hidden-import=pywintypes ^
--hidden-import=dateutil ^
--hidden-import=waitress ^
--hidden-import=webbrowser ^
--add-data "assets;assets" ^
--add-data "templates;templates" ^
--add-data "static;static" ^
--add-data "poppler;poppler" ^
"main_app.py"

if errorlevel 1 (
echo.
echo ==========================================
echo   BUILD WINDOWS 10 GAGAL
echo ==========================================
echo.
pause
exit /b 1
)

REM =========================================================
REM 8. CEK HASIL BUILD
REM =========================================================
echo.
echo [8/8] Memeriksa hasil build...
echo.

if not exist "dist_win10\MikrotikInvoice_Win10\MikrotikInvoice_Win10.exe" (
echo.
echo ==========================================
echo   [ERROR] EXE TIDAK DITEMUKAN
echo ==========================================
echo.
pause
exit /b 1
)

echo.
echo ==========================================
echo   BUILD WINDOWS 10 BERHASIL
echo ==========================================
echo.

echo Folder hasil:
echo %~dp0dist_win10\MikrotikInvoice_Win10
echo.

echo EXE:
echo %~dp0dist_win10\MikrotikInvoice_Win10\MikrotikInvoice_Win10.exe
echo.

echo ==========================================
echo   SILAKAN TEST EXE
echo ==========================================
echo.

pause
