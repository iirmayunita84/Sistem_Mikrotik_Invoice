@echo off
title TES ISOLIR - HP AKU 1

echo ============================================================
echo       TES ISOLIR PELANGGAN - HP AKU 1
echo ============================================================
echo.
echo Pelanggan : hp aku 1
echo IP        : 10.10.10.156
echo.
echo PERINGATAN:
echo Perintah berikut akan MEMUTUS akses internet pelanggan.
echo.
pause

python -c "import sqlite3,os; from core.mikrotik_api import get_router_by_id; from core.isolir_core import proses_isolir; db=os.path.join(os.environ['APPDATA'],'MikrotikInvoice','database.db'); c=sqlite3.connect(db); c.row_factory=sqlite3.Row; p=c.execute(\"SELECT * FROM pelanggan WHERE nama=?\",('hp aku 1',)).fetchone(); c.close(); print('PELANGGAN:',dict(p) if p else 'TIDAK DITEMUKAN'); router=get_router_by_id(p['user_id'],p['router_id']) if p else None; print('ROUTER:',router); hasil=proses_isolir(router,dict(p)) if router and p else False; print('HASIL ISOLIR:',hasil); raise SystemExit(0 if hasil else 1)"

if errorlevel 1 (
    echo.
    echo [ERROR] ISOLIR GAGAL
) else (
    echo.
    echo [OK] ISOLIR BERHASIL
)

echo.
echo ============================================================
echo TES SELESAI
echo ============================================================
pause