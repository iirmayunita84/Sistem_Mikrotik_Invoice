@echo off
title Build License Generator

echo ==========================================
echo    BUILD LICENSE GENERATOR
echo ==========================================
echo.

cd /d "%~dp0"

echo [1/4] Menghapus hasil build lama...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

echo.
echo [2/4] Membuat EXE...

pyinstaller --onefile --windowed --clean --icon="assets\Untitled.ico" --name "License Generator Admin" license_generator_gui.py

if errorlevel 1 (
    echo.
    echo ==========================================
    echo BUILD GAGAL
    echo ==========================================
    pause
    exit /b
)

echo.
echo ==========================================
echo BUILD BERHASIL
echo ==========================================
echo.

echo File EXE berada di:
echo %cd%\dist\License Generator Admin.exe

start "" "%cd%\dist"

pause