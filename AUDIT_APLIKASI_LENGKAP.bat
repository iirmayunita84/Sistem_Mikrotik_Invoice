@echo off
setlocal EnableExtensions EnableDelayedExpansion
title AUDIT APLIKASI MIKROTIK INVOICE - LENGKAP

cd /d "%~dp0"
set "REPORT=%CD%\AUDIT_HASIL_LENGKAP.txt"
set /a PASS=0,FAIL=0,WARN=0,INFO=0

>"%REPORT%" echo ================================================================
>>"%REPORT%" echo AUDIT APLIKASI MIKROTIK INVOICE - LENGKAP
>>"%REPORT%" echo Folder : %CD%
>>"%REPORT%" echo Tanggal: %date% %time%
>>"%REPORT%" echo ================================================================

call :section "1. LINGKUNGAN PYTHON"
call :check_python
call :check_pip
call :check_module flask Flask
call :check_module requests Requests
call :check_module sqlite3 SQLite3
call :check_module routeros_api RouterOS-API
call :check_module dateutil python-dateutil
call :check_module schedule schedule

call :section "2. FILE UTAMA"
for %%F in (main_app.py web.py) do call :check_file "%%F"
for %%F in (core\db.py core\mikrotik_core.py core\mikrotik_api.py core\license_core.py core\core_pelanggan.py core\comment_parser.py core\dhcp_core.py core\transaksi_core.py) do call :check_file "%%F"
for %%F in (routes\auth_routes.py routes\pelanggan_routes.py routes\router_routes.py routes\transaksi_routes.py routes\invoice_routes.py routes\misc_routes.py routes\setting_routes.py) do call :check_file "%%F"
for %%F in (services\payment_service.py) do call :check_file "%%F"

call :section "3. SYNTAX SEMUA PYTHON"
python -m compileall -q . >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Ada file Python gagal di-compile.
  >>"%REPORT%" echo [ERROR] Ada file Python gagal di-compile.
  python -m compileall . >>"%REPORT%" 2>&1
  set /a FAIL+=1
) else (
  echo [OK] Semua file Python berhasil di-compile.
  >>"%REPORT%" echo [OK] Semua file Python berhasil di-compile.
  set /a PASS+=1
)

call :section "4. IMPORT DAN FUNGSI PENTING"
python -c "from core.mikrotik_core import konek_mikrotik, hitung_status, auto_blokir_router, proses_pembayaran, tarik_semua_pelanggan; from core.mikrotik_api import get_pelanggan_usage, update_comment_dhcp, update_comment_pppoe, update_pppoe_user; from core.license_core import get_license_info; print('IMPORT CORE OK')" > "%TEMP%\audit_core.txt" 2>&1
if errorlevel 1 (
  echo [ERROR] Import core gagal.
  type "%TEMP%\audit_core.txt"
  >>"%REPORT%" echo [ERROR] Import core gagal.
  >>"%REPORT%" type "%TEMP%\audit_core.txt"
  set /a FAIL+=1
) else (
  echo [OK] Fungsi core utama tersedia.
  >>"%REPORT%" echo [OK] Fungsi core utama tersedia.
  set /a PASS+=1
)
del "%TEMP%\audit_core.txt" >nul 2>&1

call :section "5. DATABASE"
set "DB=%APPDATA%\MikrotikInvoice\database.db"

set "USER_ID="
for /f "delims=" %%U in ('python -c "import sqlite3; c=sqlite3.connect(r'%DB%'); r=c.execute('select id from users limit 1').fetchone(); print(r[0] if r else ''); c.close()" 2^>nul') do set "USER_ID=%%U"

if defined USER_ID (
    echo [OK] User ID ditemukan: %USER_ID%
    >>"%REPORT%" echo [OK] User ID ditemukan: %USER_ID%
) else (
    echo [WARNING] User ID tidak ditemukan.
    >>"%REPORT%" echo [WARNING] User ID tidak ditemukan.
    set /a WARN+=1
)

if exist "%DB%" (
  echo [OK] Database ditemukan: %DB%
  >>"%REPORT%" echo [OK] Database ditemukan: %DB%
  set /a PASS+=1
) else (
  echo [ERROR] Database tidak ditemukan: %DB%
  >>"%REPORT%" echo [ERROR] Database tidak ditemukan: %DB%
  set /a FAIL+=1
)

if exist "%DB%" (
  python -c "import sqlite3,sys; p=r'%DB%'; c=sqlite3.connect(p); t=[x[0] for x in c.execute(\"select name from sqlite_master where type='table' order by name\")]; print('TABLES:'); [print(' - '+x) for x in t]; req=['users','licenses','trial_info','app_config','routers','pelanggan','router_log','tagihan','transaksi','dhcp_clients','wa_log']; miss=[x for x in req if x not in t]; print('MISSING:', ', '.join(miss) if miss else 'TIDAK ADA'); c.close(); sys.exit(1 if miss else 0)" > "%TEMP%\audit_db.txt" 2>&1
  type "%TEMP%\audit_db.txt"
  >>"%REPORT%" type "%TEMP%\audit_db.txt"
  if errorlevel 1 (echo [ERROR] Tabel wajib database tidak lengkap.&set /a FAIL+=1) else (echo [OK] Tabel wajib lengkap.&set /a PASS+=1)
  del "%TEMP%\audit_db.txt" >nul 2>&1
)

call :section "6. KOLOM DATABASE PENTING"

if exist "%DB%" (
    python -c "import sqlite3,sys; c=sqlite3.connect(r'%DB%'); checks={'pelanggan':['id','user_id','router_id','tipe','nama','paket','harga','status','no_hp','jatuh_tempo','ip_address','mac_address','pppoe_username','pppoe_password','iface','usage'],'transaksi':['id','pelanggan_id','tanggal','jumlah','status'],'tagihan':['id','pelanggan_id','bulan','tahun','status'],'routers':['id','user_id','host','username','port'],'dhcp_clients':['id','user_id','router_id','ip_address','mac_address','due']}; bad=0; [print(t+': '+('OK' if not [x for x in cols if x not in [r[1] for r in c.execute('pragma table_info('+t+')')]] else 'MISSING '+','.join([x for x in cols if x not in [r[1] for r in c.execute('pragma table_info('+t+')')]]))) or (bad:=bad+bool([x for x in cols if x not in [r[1] for r in c.execute('pragma table_info('+t+')')]])) for t,cols in checks.items()]; c.close(); sys.exit(1 if bad else 0)" > "%TEMP%\audit_cols.txt" 2>&1

    type "%TEMP%\audit_cols.txt"
    >>"%REPORT%" type "%TEMP%\audit_cols.txt"

    if errorlevel 1 (
        echo [ERROR] Ada kolom database penting yang hilang.
        >>"%REPORT%" echo [ERROR] Ada kolom database penting yang hilang.
        set /a FAIL+=1
    ) else (
        echo [OK] Kolom penting lengkap.
        >>"%REPORT%" echo [OK] Kolom penting lengkap.
        set /a PASS+=1
    )

    del "%TEMP%\audit_cols.txt" >nul 2>&1
) else (
    echo [ERROR] Database tidak ditemukan.
    >>"%REPORT%" echo [ERROR] Database tidak ditemukan.
    set /a FAIL+=1
)

call :section "7. DATA DATABASE"
if exist "%DB%" (
  python -c "import sqlite3; c=sqlite3.connect(r'%DB%'); print('Users    :',c.execute('select count(*) from users').fetchone()[0]); print('Routers  :',c.execute('select count(*) from routers').fetchone()[0]); print('Pelanggan:',c.execute('select count(*) from pelanggan').fetchone()[0]); print('Tagihan  :',c.execute('select count(*) from tagihan').fetchone()[0]); print('Transaksi:',c.execute('select count(*) from transaksi').fetchone()[0]); print('DHCP     :',c.execute('select count(*) from dhcp_clients').fetchone()[0]); c.close()" > "%TEMP%\audit_counts.txt" 2>&1
  type "%TEMP%\audit_counts.txt"
  >>"%REPORT%" type "%TEMP%\audit_counts.txt"
  echo [INFO] Data database berhasil dibaca.
  >>"%REPORT%" echo [INFO] Data database berhasil dibaca.
  set /a INFO+=1
  del "%TEMP%\audit_counts.txt" >nul 2>&1
)

call :section "8. LICENSE"
python -c "from core.license_core import get_license_info; x=get_license_info(force=True); print(x)" > "%TEMP%\audit_license.txt" 2>&1
if errorlevel 1 (
  echo [ERROR] License core gagal dibaca.
  type "%TEMP%\audit_license.txt"
  >>"%REPORT%" type "%TEMP%\audit_license.txt"
  set /a FAIL+=1
) else (
  echo [OK] License core dapat dibaca.
  type "%TEMP%\audit_license.txt"
  >>"%REPORT%" type "%TEMP%\audit_license.txt"
  set /a PASS+=1
)
del "%TEMP%\audit_license.txt" >nul 2>&1

call :section "9. ROUTE FLASK"
findstr /S /N /I "@.*route" routes\*.py > "%TEMP%\audit_routes.txt" 2>nul
if errorlevel 1 (
  echo [WARNING] Route Flask tidak terdeteksi oleh findstr.
  >>"%REPORT%" echo [WARNING] Route Flask tidak terdeteksi oleh findstr.
  set /a WARN+=1
) else (
  echo [OK] Route Flask terdeteksi:
  type "%TEMP%\audit_routes.txt"
  >>"%REPORT%" type "%TEMP%\audit_routes.txt"
  set /a PASS+=1
)
del "%TEMP%\audit_routes.txt" >nul 2>&1

call :section "10. FUNGSI JADWAL / BACKGROUND"
findstr /S /N /I "auto_dhcp_sync auto_usage_sync update_data_pelanggan auto_wa_reminder scheduler schedule" *.py > "%TEMP%\audit_scheduler.txt" 2>nul
if errorlevel 1 (
  echo [WARNING] Fungsi scheduler/background tidak terdeteksi.
  >>"%REPORT%" echo [WARNING] Fungsi scheduler/background tidak terdeteksi.
  set /a WARN+=1
) else (
  echo [OK] Komponen scheduler/background terdeteksi.
  type "%TEMP%\audit_scheduler.txt"
  >>"%REPORT%" type "%TEMP%\audit_scheduler.txt"
  set /a PASS+=1
)
del "%TEMP%\audit_scheduler.txt" >nul 2>&1

call :section "10A. TEST ISOLIR OTOMATIS"

python -c "from core.mikrotik_core import auto_blokir_router; print('FUNGSI auto_blokir_router: TERSEDIA')" > "%TEMP%\audit_isolir.txt" 2>&1

if errorlevel 1 (
    echo [ERROR] Fungsi auto_blokir_router tidak dapat di-import.
    >>"%REPORT%" echo [ERROR] Fungsi auto_blokir_router tidak dapat di-import.
    type "%TEMP%\audit_isolir.txt"
    >>"%REPORT%" type "%TEMP%\audit_isolir.txt"
    set /a FAIL+=1
) else (
    echo [OK] Fungsi auto_blokir_router tersedia.
    >>"%REPORT%" echo [OK] Fungsi auto_blokir_router tersedia.
    set /a PASS+=1
)

python -c "import sqlite3,datetime; p=r'%DB%'; c=sqlite3.connect(p); c.row_factory=sqlite3.Row; today=datetime.datetime.now().date(); rows=c.execute('SELECT nama,jatuh_tempo,status FROM pelanggan WHERE user_id=?',(r'%USER_ID%',)).fetchall(); print('Tanggal hari ini:',today.strftime('%%d/%%m/%%Y')); print('Pelanggan yang perlu diperiksa:'); [print(' -',r['nama'],'|',r['jatuh_tempo'],'| status=',r['status']) for r in rows]; c.close()" > "%TEMP%\audit_isolir_data.txt" 2>&1

type "%TEMP%\audit_isolir_data.txt"
>>"%REPORT%" type "%TEMP%\audit_isolir_data.txt"

python -c "import sqlite3; p=r'%DB%'; c=sqlite3.connect(p); c.row_factory=sqlite3.Row; rows=c.execute(\"SELECT p.nama,p.jatuh_tempo,t.status FROM pelanggan p LEFT JOIN tagihan t ON t.pelanggan_id=p.id AND t.user_id=p.user_id WHERE p.user_id=? AND UPPER(COALESCE(t.status,'')) NOT IN ('LUNAS','PAID','SUDAH BAYAR','SUDAH DIBAYAR')\",(r'%USER_ID%',)).fetchall(); print('CALON ISOLIR:'); [print(' -',r['nama'],'| jatuh tempo=',r['jatuh_tempo'],'| tagihan=',r['status']) for r in rows]; print('Total calon isolir:',len(rows)); c.close()" > "%TEMP%\audit_calon_isolir.txt" 2>&1

type "%TEMP%\audit_calon_isolir.txt"
>>"%REPORT%" type "%TEMP%\audit_calon_isolir.txt"

del "%TEMP%\audit_isolir.txt" >nul 2>&1
del "%TEMP%\audit_isolir_data.txt" >nul 2>&1
del "%TEMP%\audit_calon_isolir.txt" >nul 2>&1

call :section "11. DHCP / PPPOE / PEMBAYARAN"
for %%K in (DHCP PPPOE pembayaran jatuh_tempo blokir unblokir invoice whatsapp reminder) do (
  findstr /S /N /I "%%K" *.py > "%TEMP%\audit_%%K.txt" 2>nul
  if errorlevel 1 (
    echo [WARNING] Keyword %%K tidak ditemukan.
    >>"%REPORT%" echo [WARNING] Keyword %%K tidak ditemukan.
    set /a WARN+=1
  ) else (
    echo [OK] Komponen %%K terdeteksi.
    >>"%REPORT%" echo [OK] Komponen %%K terdeteksi.
    set /a PASS+=1
  )
  del "%TEMP%\audit_%%K.txt" >nul 2>&1
)

call :section "12. TANGGAL"
findstr /S /N /I "%d/%m/%Y %Y-%m-%d jatuh_tempo tanggal_bayar" *.py > "%TEMP%\audit_date.txt" 2>nul
if errorlevel 1 (
  echo [WARNING] Pola tanggal tidak terdeteksi.
  >>"%REPORT%" echo [WARNING] Pola tanggal tidak terdeteksi.
  set /a WARN+=1
) else (
  echo [INFO] Pemeriksaan pola tanggal:
  type "%TEMP%\audit_date.txt"
  >>"%REPORT%" type "%TEMP%\audit_date.txt"
  set /a INFO+=1
)
del "%TEMP%\audit_date.txt" >nul 2>&1

call :section "13. POLA ERROR UMUM"
for %%K in (NameError ImportError IndentationError SyntaxError get_pelanggan_usage get_license_info konek_mikrotik) do (
  findstr /S /N /I "%%K" *.py > "%TEMP%\audit_err.txt" 2>nul
  if errorlevel 1 (
    echo [INFO] %%K tidak ditemukan dalam source.
    >>"%REPORT%" echo [INFO] %%K tidak ditemukan dalam source.
    set /a INFO+=1
  ) else (
    echo [INFO] %%K ditemukan dalam source - perlu interpretasi, bukan otomatis error.
    >>"%REPORT%" echo [INFO] %%K ditemukan dalam source - perlu interpretasi, bukan otomatis error.
    set /a INFO+=1
  )
  del "%TEMP%\audit_err.txt" >nul 2>&1
)

call :section "14. FILE BACKUP"
if exist "%APPDATA%\MikrotikInvoice\database.db" (
  echo [INFO] Database aktif tersedia. Pastikan mekanisme backup juga tersedia sebelum penjualan.
  >>"%REPORT%" echo [INFO] Database aktif tersedia. Pastikan mekanisme backup juga tersedia sebelum penjualan.
  set /a WARN+=1
)

call :section "15. STARTUP TEST"
echo [INFO] Menjalankan startup test singkat. Tidak dilakukan jika port 5000 sedang dipakai.
>>"%REPORT%" echo [INFO] Startup test singkat.
python -c "import socket; s=socket.socket(); r=s.connect_ex(('127.0.0.1',5000)); s.close(); print('PORT 5000:', 'SEDANG DIPAKAI' if r==0 else 'TIDAK DIPAKAI')" > "%TEMP%\audit_port.txt" 2>&1
type "%TEMP%\audit_port.txt"
>>"%REPORT%" type "%TEMP%\audit_port.txt"
if not errorlevel 1 set /a INFO+=1
del "%TEMP%\audit_port.txt" >nul 2>&1

echo.
echo ================================================================
echo                       HASIL AKHIR AUDIT
echo ================================================================
echo LULUS    : %PASS%
echo ERROR    : %FAIL%
echo WARNING  : %WARN%
echo INFO     : %INFO%
echo ================================================================
>>"%REPORT%" echo ================================================================
>>"%REPORT%" echo HASIL AKHIR AUDIT
>>"%REPORT%" echo LULUS    : %PASS%
>>"%REPORT%" echo ERROR    : %FAIL%
>>"%REPORT%" echo WARNING  : %WARN%
>>"%REPORT%" echo INFO     : %INFO%
>>"%REPORT%" echo ================================================================

if %FAIL% EQU 0 (
 echo STATUS: TIDAK ADA ERROR TEKNIS UTAMA TERDETEKSI
 >>"%REPORT%" echo STATUS: TIDAK ADA ERROR TEKNIS UTAMA TERDETEKSI
) else (
 echo STATUS: ADA ERROR - JANGAN JUAL SEBELUM DIPERBAIKI
 >>"%REPORT%" echo STATUS: ADA ERROR - JANGAN JUAL SEBELUM DIPERBAIKI
)

echo.
echo Laporan: %REPORT%
echo.
pause
exit /b

:section
echo.
echo ================================================================
echo %~1
echo ================================================================
>>"%REPORT%" echo.
>>"%REPORT%" echo ================================================================
>>"%REPORT%" echo %~1
>>"%REPORT%" echo ================================================================
exit /b

:check_python
python --version >nul 2>&1
if errorlevel 1 (
 echo [ERROR] Python tidak ditemukan.
 >>"%REPORT%" echo [ERROR] Python tidak ditemukan.
 set /a FAIL+=1
) else (
 for /f "delims=" %%A in ('python --version 2^>^&1') do echo [OK] %%A
 python --version >>"%REPORT%" 2>&1
 set /a PASS+=1
)
exit /b

:check_pip
python -m pip --version >nul 2>&1
if errorlevel 1 (
 echo [WARNING] pip tidak tersedia.
 >>"%REPORT%" echo [WARNING] pip tidak tersedia.
 set /a WARN+=1
) else (
 echo [OK] pip tersedia.
 >>"%REPORT%" echo [OK] pip tersedia.
 set /a PASS+=1
)
exit /b

:check_module
python -c "import %~1; print('%~2 OK')" >nul 2>&1
if errorlevel 1 (
 echo [ERROR] Modul %~2 tidak bisa di-import.
 >>"%REPORT%" echo [ERROR] Modul %~2 tidak bisa di-import.
 set /a FAIL+=1
) else (
 echo [OK] Modul %~2
 >>"%REPORT%" echo [OK] Modul %~2
 set /a PASS+=1
)
exit /b

:check_file
if exist "%~1" (
 echo [OK] %~1
 >>"%REPORT%" echo [OK] %~1
 set /a PASS+=1
) else (
 echo [WARNING] File tidak ditemukan: %~1
 >>"%REPORT%" echo [WARNING] File tidak ditemukan: %~1
 set /a WARN+=1
)
exit /b
