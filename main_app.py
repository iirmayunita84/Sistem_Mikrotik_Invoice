# main_app.py 
import sys

import threading
import time
from datetime import datetime
import webbrowser
import logging
try:
    import pyi_splash
    pyi_splash.close()
except Exception:
    pass

from core.db import init_db

init_db()

from web import app

from core.premium import check_trial, is_premium
from core.license_core import (
    get_license_info,
    get_device_id,
    license_valid_local,
    simpan_license,
    validasi_kode_aktivasi,
)
from core.mikrotik_api import (
    update_comment_dhcp,
    update_comment_pppoe,
    update_pppoe_user,
    get_pelanggan_usage,
    sync_dhcp_ip_binding,
    binding_dhcp_pelanggan,
)

from core.mikrotik_core import (
    konek_mikrotik,
    auto_blokir_router,
    proses_pembayaran,
    tarik_semua_pelanggan,
    hitung_status,
    sinkron_binding_dhcp_user,
)

from services.wa_service import (
    kirim_reminder_massal
)
from core.api import sinkron_semua_router
from core.logic import (
    get_all_users,
    generate_pelanggan_dari_dhcp,
    load_mikrotik_list,
)

from core.config_core import (
    get_app_config,
)

from core.admin_login import show_admin_login
from waitress import serve

# =========================
# PyInstaller safe guard
# =========================
def is_frozen():
    return getattr(sys, 'frozen', False)

# =========================
# Logging
# =========================
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
def log(msg):
    print(msg)
    logging.info(msg)

import atexit


def shutdown():
    log("🛑 Aplikasi ditutup")


atexit.register(shutdown)
# =========================
# Background: DHCP sync
# =========================
def auto_dhcp_sync():
    try:
        users = get_all_users()

        if not users:
            print("Tidak ada user.")
            return

        grand_total = 0
        grand_static = 0

        for user in users:

            user_id = user["id"]

            print("\n" + "=" * 60)
            print(f"DHCP SYNC USER: {user['username']}")
            print("=" * 60)

            # ==========================================
            # 1. SYNC DATA DHCP DARI MIKROTIK
            # ==========================================

            total = sinkron_semua_router(user_id)

            grand_total += total

            print(
                f"✅ {user['username']} -> "
                f"{total} DHCP"
            )

            # ==========================================
            # 2. BINDING DHCP PELANGGAN
            # ==========================================

            static_total = sinkron_binding_dhcp_user(
                user_id
            )

            grand_static += static_total

            print(
                f"🔐 {user['username']} -> "
                f"{static_total} DHCP STATIC"
            )

        print("\n" + "=" * 60)
        print("🎉 DHCP SYNC SELESAI")
        print("=" * 60)

        print(
            f"Total DHCP        : {grand_total}"
        )

        print(
            f"Total DHCP STATIC : {grand_static}"
        )

        print("=" * 60)

    except Exception as e:
        print(
            "❌ DHCP sync error:",
            e
        )

# =========================
# IDENTITAS PELANGGAN
# =========================
def get_identitas_pelanggan(p):

    username = (
        p.get("pppoe_username")
        or p.get("pppoe_user")
        or ""
    ).strip()

    if username:
        return f"PPPOE:{username.lower()}"

    mac = (
        p.get("mac_address")
        or p.get("mac")
        or ""
    ).strip()

    if mac:
        return f"MAC:{mac.upper()}"

    ip = (
        p.get("ip_address")
        or p.get("ip")
        or ""
    ).strip()

    if ip:
        return f"IP:{ip}"

    return None

# =========================
# NORMALISASI TANGGAL
# FORMAT RESMI APLIKASI:
# DD/MM/YYYY
# =========================
def normalisasi_tanggal(tanggal):

    if not tanggal:
        return ""

    tanggal = str(tanggal).strip()

    # Format resmi: DD/MM/YYYY
    try:
        return datetime.strptime(
            tanggal,
            "%d/%m/%Y"
        ).strftime("%d/%m/%Y")
    except ValueError:
        pass

    # Input ISO dari HTML/date picker: YYYY-MM-DD
    try:
        return datetime.strptime(
            tanggal,
            "%Y-%m-%d"
        ).strftime("%d/%m/%Y")
    except ValueError:
        pass

    # Jangan menebak MM/DD/YYYY.
    # Format ambigu harus ditolak/diperbaiki dari sumbernya.
    return ""

# =========================
# Background: Usage sync
# =========================
def auto_usage_sync():

    from core.core_pelanggan import (
        get_pelanggan_list,
        update_pelanggan
    )

    try:

        users = get_all_users()

        for user in users:

            user_id = user["id"]

            routers = load_mikrotik_list(
                user_id
            )

            pelanggan_local = (
                get_pelanggan_list(
                    user_id=user_id
                )
            )

            for router in routers:

                api = None
                conn = None

                try:

                    api, conn = konek_mikrotik(
                        router
                    )

                    if not api:
                        print(
                            "❌ Router tidak terkoneksi:",
                            router.get("host")
                        )
                        continue

                    # ======================================
                    # AMBIL DATA PELANGGAN LOKAL
                    # ======================================

                    for pelanggan in pelanggan_local:

                        router_id = pelanggan.get(
                            "router_id"
                        )

                        if str(router_id) != str(
                            router.get("id")
                        ):
                            continue

                        tipe = str(
                            pelanggan.get("tipe") or ""
                        ).upper()

                        if tipe not in (
                            "DHCP",
                            "PPPOE"
                        ):
                            continue

                        # ==================================
                        # AMBIL USAGE DARI MIKROTIK
                        # ==================================

                        usage_gb = get_pelanggan_usage(
                            api,
                            pelanggan
                        )

                        usage_text = (
                            f"{usage_gb:.2f}GB"
                        )

                        print(
                            "📊 USAGE:",
                            pelanggan.get("nama"),
                            "|",
                            tipe,
                            "|",
                            usage_text
                        )

                        # ==================================
                        # SIMPAN
                        # ==================================

                        data_update = dict(
                            pelanggan
                        )

                        data_update[
                            "usage"
                        ] = usage_text

                        data_update[
                            "usage_last"
                        ] = usage_text

                        update_pelanggan(
                            user_id,
                            pelanggan["id"],
                            data_update
                        )

                except Exception as e:

                    print(
                        "❌ Usage sync router gagal:",
                        e
                    )

                finally:

                    if conn:

                        try:
                            conn.disconnect()

                        except Exception:
                            pass

    except Exception:

        logging.exception(
            "Usage sync error"
        )
# =========================
# Update Data Pelanggan & Generate Invoice Otomatis
# =========================
def update_data_pelanggan():
    
    from core.core_pelanggan import (
        get_pelanggan_list,
        tambah_pelanggan,
        update_pelanggan,
        refresh_pelanggan_cache,
        generate_invoice_semua
    )

    print("⏳ Background pelanggan & invoice service aktif")

    try:
        users = get_all_users()
        now = datetime.now()

        for user in users:

            user_id = user["id"]

            routers = load_mikrotik_list(user_id)

            # =========================
            # CACHE PELANGGAN
            # PPPoE = username
            # DHCP = MAC Address
            # =========================
            data_local = {}

            for p in get_pelanggan_list(user_id=user_id):

                identitas = get_identitas_pelanggan(p)

                if identitas:
                    data_local[identitas] = p

            for r in routers:

                api, conn = konek_mikrotik(r)

                if not api:
                    continue

                try:          

                    pelanggan_router = tarik_semua_pelanggan(
                        api,
                        r["id"]
                    )

                    # ==================================================
                    # DHCP + PPPOE
                    # ==================================================

                    for p_router in pelanggan_router:

                        tipe = str(
                            p_router.get("tipe") or ""
                        ).upper()

                        # ===============================================
                        # DHCP
                        # ===============================================

                        if tipe == "DHCP":

                            try:

                                p_router = sync_dhcp_ip_binding(
                                    api,
                                    p_router
                                )

                            except Exception as e:

                                print(
                                    f"⚠️ DHCP binding gagal "
                                    f"{p_router.get('nama')}: {e}"
                                )

                        # ===============================================
                        # LANJUTKAN PROSES NORMAL
                        # ===============================================

                    for p_router in pelanggan_router:

                        # Ambil identitas pelanggan
                        identitas = get_identitas_pelanggan(
                            p_router
                        )

                        if not identitas:

                            print(
                                "⚠️ Pelanggan dilewati, "
                                "identitas tidak ditemukan:",
                                p_router.get("nama")
                            )

                            continue

                        # Cari pelanggan yang sudah ada
                        existing = data_local.get(
                            identitas
                        )

                        # =========================
                        # NORMALISASI JATUH TEMPO
                        # =========================

                        due_router = normalisasi_tanggal(
                            p_router.get("due")
                        )

                        status_baru = hitung_status(
                            due_router,
                            None
                        )
                        if existing:

                            perubahan = False

                            # =====================================================
                            # DHCP BINDING AMAN
                            # MAC = IDENTITAS
                            # IP DATABASE TIDAK BOLEH BERUBAH OTOMATIS
                            # =====================================================

                            tipe_existing = str(
                                existing.get("tipe")
                                or p_router.get("tipe")
                                or ""
                            ).upper()

                            ip_router = (
                                p_router.get("ip") or ""
                            ).strip()

                            mac_router = (
                                p_router.get("mac") or ""
                            ).strip().upper()

                            ip_db = (
                                existing.get("ip_address") or ""
                            ).strip()

                            mac_db = (
                                existing.get("mac_address") or ""
                            ).strip().upper()

                            if tipe_existing == "DHCP":

                                # MAC adalah identitas DHCP.
                                # Jangan mengganti MAC yang sudah tersimpan.
                                if mac_db and mac_router and mac_db != mac_router:

                                    print(
                                        f"DHCP MISMATCH MAC | "
                                        f"{existing.get('nama')} | "
                                        f"DB={mac_db} | "
                                        f"MIKROTIK={mac_router} | "
                                        f"MAC DATABASE TIDAK DIUBAH"
                                    )

                                elif not mac_db and mac_router:

                                    existing["mac_address"] = mac_router
                                    perubahan = True

                                    print(
                                        f"MAC DHCP tersimpan | "
                                        f"{existing.get('nama')} | "
                                        f"MAC={mac_router}"
                                    )

                                # IP yang sudah tersimpan menjadi IP tetap pelanggan.
                                if ip_db and ip_router and ip_db != ip_router:

                                    print(
                                        f"DHCP MISMATCH IP | "
                                        f"{existing.get('nama')} | "
                                        f"IP DATABASE={ip_db} | "
                                        f"IP MIKROTIK={ip_router} | "
                                        f"IP DATABASE TIDAK DIUBAH"
                                    )

                                elif not ip_db and ip_router:

                                    existing["ip_address"] = ip_router
                                    perubahan = True

                                    print(
                                        f"IP DHCP tersimpan | "
                                        f"{existing.get('nama')} | "
                                        f"IP={ip_router}"
                                    )

                                # Data non-binding tetap boleh disinkronkan.
                                mapping = {
                                    "usage": "usage_last",
                                    "paket": "paket",
                                    "harga": "harga",
                                    "nama": "nama",
                                    "no_hp": "no_hp",
                                }

                            else:

                                # PPPoE tetap menggunakan sinkronisasi normal.
                                mapping = {
                                    "usage": "usage_last",
                                    "ip": "ip_address",
                                    "mac": "mac_address",
                                    "paket": "paket",
                                    "harga": "harga",
                                    "nama": "nama",
                                    "no_hp": "no_hp",
                                }

                            for src, dst in mapping.items():

                                nilai_baru = p_router.get(src)

                                if existing.get(dst) != nilai_baru:

                                    print(
                                        f"UPDATE {existing.get('nama')} "
                                        f"{dst}: "
                                        f"{existing.get(dst)} "
                                        f"-> {nilai_baru}"
                                    )

                                    existing[dst] = nilai_baru
                                    perubahan = True

                            if existing.get("router_id") != r["id"]:

                                existing["router_id"] = r["id"]
                                perubahan = True

                            # =====================================================
                            # STATUS DITENTUKAN DARI JATUH TEMPO DATABASE
                            # =====================================================

                            due_db = normalisasi_tanggal(
                                existing.get("jatuh_tempo")
                            )

                            if due_db:

                                status_db_baru = hitung_status(
                                    due_db,
                                    None
                                )

                                if existing.get("status") != status_db_baru:

                                    print(
                                        f"UPDATE {existing.get('nama')} status: "
                                        f"{existing.get('status')} "
                                        f"-> {status_db_baru}"
                                    )

                                    existing["status"] = status_db_baru
                                    perubahan = True

                            if perubahan:

                                update_pelanggan(
                                    user_id,
                                    existing["id"],
                                    existing
                                )

                                refresh_pelanggan_cache(
                                    user_id
                                )

                                print(
                                    f"Update : {existing['nama']}"
                                )

                        else:

                            data = {
                                "router_id": r["id"],

                                "pppoe_username": (
                                    p_router.get("pppoe_username")
                                    or p_router.get("pppoe_user")
                                    or ""
                                ),

                                "nama": p_router.get("nama", ""),
                                "paket": p_router.get("paket", ""),
                                "harga": p_router.get("harga", 0),

                                "jatuh_tempo": due_router,

                                "status": status_baru,

                                "usage_last": p_router.get(
                                    "usage",
                                    "0GB"
                                ),

                                "ip_address": p_router.get(
                                    "ip",
                                    ""
                                ),

                                "mac_address": p_router.get(
                                    "mac",
                                    ""
                                ),

                                "no_hp": p_router.get(
                                    "no_hp",
                                    ""
                                )
                            }
                            tambah_pelanggan(user_id, data)

                            print(f"➕ Pelanggan baru : {data['nama']}")

                finally:

                    try:
                        conn.disconnect()
                    except Exception:
                        pass


 
            # ==========================================
            # GENERATE INVOICE OTOMATIS
            # Satu kali untuk setiap user
            # ==========================================

            total = generate_invoice_semua(user_id)

            if total:
                print(f"🧾 {total} invoice baru dibuat")

            print("✅ Pemeriksaan invoice selesai")

    except Exception as e:
        print(f"[WARN] Sinkron pelanggan gagal : {e}")

# =========================
# WA Reminder
# =========================
def auto_wa_reminder():

    try:
        users = get_all_users()

        for user in users:
            user_id = user["id"]
            app_config = get_app_config(user_id)

            for h in (-3, -1, 0):
                kirim_reminder_massal(
                    user_id,
                    app_config,
                    hari=h
                )
        log("📨 WA reminder OK")

    except Exception as e:
        log(f"[WARN] WA reminder gagal: {e}")

# =========================
# Auto Block Scheduler
# =========================
def auto_block_scheduler():

    print("")
    print("========================================")
    print("🔍 AUTO BLOKIR DIMULAI")
    print("========================================")

    try:

        users = get_all_users()

        print(f"👥 Jumlah user: {len(users)}")

        for user in users:

            user_id = user["id"]

            print(
                f"➡️ Cek user: {user_id}"
            )

            routers = load_mikrotik_list(user_id)

            print(
                f"   Router ditemukan: {len(routers)}"
            )

            if not routers:
                continue

            for router in routers:

                if not isinstance(router, dict):

                    print(
                        "⚠️ Router invalid:",
                        router
                    )

                    continue

                print(
                    f"🌐 Cek router: "
                    f"{router.get('host', '-')}"
                )

                auto_blokir_router(router)

        print("========================================")
        print("✅ AUTO BLOKIR SELESAI")
        print("========================================")
        print("")

    except Exception as e:

        print(
            f"❌ Auto blokir error: {e}"
        )

# =========================
# Browser Launcher
# =========================
def open_browser(url="http://127.0.0.1:5000"):

    time.sleep(3)

    for _ in range(10):
        try:
            import urllib.request
            urllib.request.urlopen(url)
            webbrowser.open(url)
            return
        except:
            time.sleep(0.5)

# =========================
# Flask Runner
# =========================
def run_flask():
    log("🚀 Menjalankan Flask (Production Mode)")
    serve(app, host="127.0.0.1", port=5000)

def on_admin_login_success():
    log("🔐 Admin login berhasil")

class TaskScheduler:

    def __init__(self):
        self.tasks = []

    def add_task(self, func, interval):
        self.tasks.append({
            "func": func,
            "interval": interval,
            "last_run": 0,
            "running": False
        })

    def run_forever(self):

        print("🟢 TASK SCHEDULER BERJALAN")

        while True:

            now = time.time()

            for task in self.tasks:

                if task["running"]:
                    continue

                if now - task["last_run"] >= task["interval"]:

                    def runner(t=task):

                        try:
                            t["running"] = True

                            print(
                                f"⏰ Menjalankan task: "
                                f"{t['func'].__name__}"
                            )

                            t["func"]()

                            print(
                                f"✅ Task selesai: "
                                f"{t['func'].__name__}"
                            )

                        except Exception as e:

                            print(
                                f"❌ Scheduler error "
                                f"{t['func'].__name__}: {e}"
                            )

                        finally:

                            t["last_run"] = time.time()
                            t["running"] = False

                    threading.Thread(
                        target=runner,
                        daemon=True
                    ).start()

            time.sleep(1)

# =========================
# MAIN
# =========================

if __name__ == "__main__":

    print("✅ Database & tabel pelanggan siap")

    info = get_license_info()

    license_blocked = info["status"] in [
        "INVALID_OR_EXPIRED",
        "NO_LICENSE",
        "CORRUPT"
    ]


    if info["status"] == "TRIAL":

        log(
            f"🧪 Mode Trial aktif ({info.get('sisa',0)} hari tersisa)"
        )


    elif license_blocked:

        log(
            "🔒 License tidak aktif. Mengarahkan ke halaman aktivasi..."
        )

        threading.Thread(
            target=open_browser,
            args=("http://127.0.0.1:5000/aktivasi",),
            daemon=True
        ).start()


    else:

        log(
            "✅ License Premium aktif"
        )


    # =========================
    # Background Threads
    # =========================

    scheduler = TaskScheduler()


    scheduler.add_task(
        auto_dhcp_sync,
        1800
    )

    scheduler.add_task(
        update_data_pelanggan,
        1800
    )
    scheduler.add_task(
        auto_usage_sync,
        1800
    )
    scheduler.add_task(
        auto_wa_reminder,
        3600
    )

    scheduler.add_task(
        auto_block_scheduler,
        120
    )

    threading.Thread(
        target=scheduler.run_forever,
        daemon=True
    ).start()

    threading.Thread(
        target=open_browser,
        daemon=True
    ).start()

    run_flask()