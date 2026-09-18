
@echo off
setlocal EnableExtensions
title TES AUTO BLOKIR - MIKROTIK INVOICE

cd /d D:\mikrotik_invoice

echo ============================================================
echo       TES AUTO BLOKIR / ISOLIR MIKROTIK INVOICE
echo ============================================================
echo.

set "ERROR_COUNT=0"

echo [1] CEK FILE

if exist "main_app.py" (
    echo [OK] main_app.py
) else (
    echo [ERROR] main_app.py tidak ditemukan
    set /a ERROR_COUNT+=1
)

if exist "core\mikrotik_core.py" (
    echo [OK] core\mikrotik_core.py
) else (
    echo [ERROR] core\mikrotik_core.py tidak ditemukan
    set /a ERROR_COUNT+=1
)

if exist "core\isolir_core.py" (
    echo [OK] core\isolir_core.py
) else (
    echo [ERROR] core\isolir_core.py tidak ditemukan
    set /a ERROR_COUNT+=1
)

if exist "core\mikrotik_api.py" (
    echo [OK] core\mikrotik_api.py
) else (
    echo [ERROR] core\mikrotik_api.py tidak ditemukan
    set /a ERROR_COUNT+=1
)

echo.
echo [2] CEK SYNTAX

python -m py_compile main_app.py >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Syntax main_app.py
    set /a ERROR_COUNT+=1
) else (
    echo [OK] main_app.py
)

python -m py_compile core\mikrotik_core.py >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Syntax core\mikrotik_core.py
    set /a ERROR_COUNT+=1
) else (
    echo [OK] core\mikrotik_core.py
)

python -m py_compile core\isolir_core.py >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Syntax core\isolir_core.py
    set /a ERROR_COUNT+=1
) else (
    echo [OK] core\isolir_core.py
)

echo.
echo [3] CEK FUNGSI ISOLIR

findstr /R /C:"def proses_isolir" core\isolir_core.py >nul
if errorlevel 1 (
    echo [ERROR] proses_isolir
    set /a ERROR_COUNT+=1
) else (
    echo [OK] proses_isolir
)

findstr /R /C:"def hapus_isolir" core\isolir_core.py >nul
if errorlevel 1 (
    echo [ERROR] hapus_isolir
    set /a ERROR_COUNT+=1
) else (
    echo [OK] hapus_isolir
)

findstr /R /C:"def auto_blokir_router" core\mikrotik_core.py >nul
if errorlevel 1 (
    echo [ERROR] auto_blokir_router
    set /a ERROR_COUNT+=1
) else (
    echo [OK] auto_blokir_router
)

echo.
echo [4] CEK DATABASE

python -c "import sqlite3,os; db=os.path.join(os.environ['APPDATA'],'MikrotikInvoice','database.db'); print('DB:',db); c=sqlite3.connect(db); print('PELANGGAN:',c.execute('SELECT COUNT(*) FROM pelanggan').fetchone()[0]); print('TAGIHAN:',c.execute('SELECT COUNT(*) FROM tagihan').fetchone()[0]); print('TRANSAKSI:',c.execute('SELECT COUNT(*) FROM transaksi').fetchone()[0]); c.close()"

if errorlevel 1 (
    echo [ERROR] Database gagal dibaca
    set /a ERROR_COUNT+=1
) else (
    echo [OK] Database bisa dibaca
)

echo.
echo [5] STRUKTUR TAGIHAN

python -c "import sqlite3,os; db=os.path.join(os.environ['APPDATA'],'MikrotikInvoice','database.db'); c=sqlite3.connect(db); print(c.execute('PRAGMA table_info(tagihan)').fetchall()); c.close()"

if errorlevel 1 (
    echo [ERROR] Gagal membaca struktur tagihan
    set /a ERROR_COUNT+=1
) else (
    echo [OK] Struktur tagihan terbaca
)

echo.
echo [6] DAFTAR PELANGGAN

python -c "import sqlite3,os; db=os.path.join(os.environ['APPDATA'],'MikrotikInvoice','database.db'); c=sqlite3.connect(db); rows=c.execute('SELECT id,nama,tipe,ip_address,status FROM pelanggan ORDER BY nama').fetchall(); print(''); [print(r) for r in rows]; c.close()"

if errorlevel 1 (
    echo [ERROR] Gagal membaca pelanggan
    set /a ERROR_COUNT+=1
) else (
    echo [OK] Data pelanggan terbaca
)

echo.
echo [7] DAFTAR TAGIHAN

python -c "import sqlite3,os; db=os.path.join(os.environ['APPDATA'],'MikrotikInvoice','database.db'); c=sqlite3.connect(db); rows=c.execute('SELECT id,pelanggan_id,bulan,tahun,jumlah,status,tanggal_bayar FROM tagihan ORDER BY tahun DESC,bulan DESC').fetchall(); print(''); [print(r) for r in rows] if rows else print('BELUM ADA TAGIHAN'); c.close()"

if errorlevel 1 (
    echo [ERROR] Gagal membaca tagihan
    set /a ERROR_COUNT+=1
) else (
    echo [OK] Data tagihan terbaca
)

echo.
echo [8] CEK DAFTAR ROUTER
echo.
echo Pemeriksaan router tidak akan mengubah data MikroTik.
echo.

python -c "import sqlite3,os; from core.logic import load_mikrotik_list; db=os.path.join(os.environ['APPDATA'],'MikrotikInvoice','database.db'); c=sqlite3.connect(db); row=c.execute('SELECT id FROM users LIMIT 1').fetchone(); c.close(); print('USER ID:',row[0] if row else 'TIDAK ADA'); routers=load_mikrotik_list(row[0]) if row else []; print('JUMLAH ROUTER:',len(routers)); [print('ROUTER:',r.get('id'),r.get('host'),r.get('label','')) for r in routers]"

if errorlevel 1 (
    echo [ERROR] Gagal membaca router
    set /a ERROR_COUNT+=1
) else (
    echo [OK] Daftar router berhasil dibaca
)

echo.


echo ============================================================
echo HASIL PEMERIKSAAN
echo ============================================================
echo JUMLAH ERROR: %ERROR_COUNT%
echo.

if not "%ERROR_COUNT%"=="0" (
    echo Ada error. JANGAN jalankan AUTO BLOCK.
    echo Perbaiki error terlebih dahulu.
    echo.
    pause
    exit /b 1
)

echo Semua pemeriksaan dasar berhasil.
echo.
echo ============================================================
echo PERINGATAN
echo ============================================================
echo.
echo DATABASE SAAT INI TIDAK BOLEH DIMANIPULASI UNTUK TES
echo sampai kita menentukan pelanggan TEST yang aman.
echo.
echo BAT ini BELUM menjalankan proses_isolir.
echo BAT ini BELUM mengubah status tagihan.
echo BAT ini BELUM memblokir pelanggan.
echo.
echo ============================================================
echo TES SELESAI - MODE AMAN
echo ============================================================
echo.

pause

